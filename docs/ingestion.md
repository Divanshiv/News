# RSS Ingestion (Phase 3)

Ingestion pulls items from registered RSS/Atom feeds into the `stories` table as
`DISCOVERED` stories linked to their source. A second run over the same feeds
is idempotent: already-seen items are skipped.

## Pipeline

```
RSS/Atom feed → fetch (httpx) → parse (feedparser) → normalize → dedup → save Story + StorySource
```

| Step | Module | Behavior |
|------|--------|----------|
| Fetch | `app/services/rss/fetch.py` | `RSSFetcher` — timeout 20s, up to 2 retries with 0.6s backoff, follows redirects. Raises `RSSFetchError` on non-2xx/network failure. |
| Parse | `app/services/rss/parse.py` | `parse_feed` — supports RSS 2.0 and Atom. Items need a title + link; relative links resolve against the source URL; HTML in summaries is stripped; dates are parsed to UTC (RFC 822 / ISO 8601); image comes from Media RSS thumbnails, `media:content`, or image enclosures. Malformed feeds yield an error, not an exception. |
| Normalize | `app/services/rss/normalize.py` | `canonicalize_url` — lowercase scheme/host, drop default ports, strip fragments and known tracking params (`utm_*`, `fbclid`, `gclid`, `gclsrc`, `dclid`, `igshid`, `mc_cid`, `mc_eid`, `ref`, `ref_src`, `ref_url`), collapse duplicate slashes. `normalize_title` — collapse whitespace + casefold. |
| Dedup | `app/services/ingestion.py` | A story is a duplicate when (a) its canonical URL already exists in `stories`, or (b) the same source already has a story with the same normalized title within the last 7 days. Duplicates are skipped. Deeper title-similarity / multi-source merging is Phase 4. |
| Link | `app/services/ingestion.py` | New stories are saved in `DISCOVERED` status with `category` copied from the source, then linked via `StorySource` (`relationship_note` = `primary`). If the same story already exists from another source, the new source is linked instead as `secondary` (relevance 0.9) without re-creating the story. |

Each fetched source records `last_fetched_at`; failures also record
`last_fetch_error` on the source row.

## API

All endpoints return `202 Accepted` with a job id — the actual fetching runs in
the background job runner; poll the job endpoint until it is `COMPLETED` or
`FAILED`.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/ingestion/run` | Ingest all active sources with an `rss_url`. |
| POST | `/api/v1/ingestion/sources/{source_id}/fetch` | Ingest a single source (404 if unknown, 400 if it has no RSS URL). |
| GET | `/api/v1/ingestion/jobs/{job_id}` | Job status + per-source results (`fetched`, `created`, `skipped`, `error`). |

Job responses:

```json
202 {"job_id": "…", "job_name": "ingest_all", "status": "QUEUED"}
```

```json
{
  "job_id": "…",
  "job_name": "ingest_all",
  "status": "COMPLETED",
  "created_at": "…", "started_at": "…", "completed_at": "…",
  "error": null,
  "result": [
    {"source_id": 1, "source_name": "Ars Technica", "status": "ok",
     "fetched": 20, "created": 0, "skipped": 20, "error": null}
  ]
}
```

## Dashboard

- `/dashboard/stories` — ingested stories (title, source chips, category,
  status, discovered time) with a "Run ingestion" action.
- `/dashboard/sources` — source registry (feed URL, category, type,
  reliability, active flag, last fetch status/error/time) with "Ingest all"
  and per-source fetch actions.

Both pages poll the job endpoint every 1.2s with a 60s timeout, then refresh
the table.

## Job runner

`app/workers/jobs.py` provides an in-process async `JobRunner` (2 workers).
Jobs are tracked in memory; handlers are registered at import time in
`app/workers/ingestion.py`. For multi-worker deployments, swap for Redis + ARQ
keeping the `submit`/`get` interface.

## Testing

`tests/test_rss_normalize.py`, `tests/test_rss_parse.py`,
`tests/test_ingestion.py`, `tests/test_api_ingestion.py` cover the pipeline
with fixture feeds (RSS, Atom, malformed, duplicate-title). API tests bypass
the network by registering fake handlers on a reset `job_runner` via
`tests/conftest.py`.