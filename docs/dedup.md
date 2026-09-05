# Deduplication & Story Merging (Phase 4)

Goal: **one event = one story with multiple sources**. Stories about the same
news event arriving from different feeds converge on a single canonical row
whose `story_sources` links carry the full set of covering sources.

## How duplicates are decided

Exact and fuzzy rules live in `app/services/dedup/similarity.py` (stdlib only —
no ML, no scikit-learn). All text is tokenized after stopword stripping; titles
compare via max(token Jaccard, `difflib.SequenceMatcher.ratio`).

| Rule | Condition | Effect |
|------|-----------|--------|
| R1 strong title | `title_sim >= 0.85` | duplicate |
| R2 title + summary | `title_sim >= 0.75` **and** `desc_sim >= 0.75` (descriptions shorter than 20 chars are ignored) | duplicate |
| R3 token containment | both titles have ≥ 3 tokens and `containment >= 0.75` | duplicate |

`pair_score = 0.7 * title_sim + 0.3 * desc_sim` (desc-only when unavailable) is
used to rank candidates and for the review API.

## Ingestion-time behavior

`app/services/ingestion.py::_find_match` runs per item, in order:

1. **Exact canonical URL** (all time, any source) — link-only, no merge.
2. **Same source, same normalized title** (last 7 days) — preserves the P3
   same-feed dedup guarantee.
3. **Fuzzy cross-source** — the last 7 days' stories (capped at 300, newest
   first), **excluding stories already linked to the incoming source**, scored
   with the rules above. The best-scoring match gets the new source link as
   `secondary`.

Ingestion never merges stories (avoids races with concurrent source fetches).
Merging is the maintenance job's job.

## The dedupe maintenance job

`app/workers/dedup.py::handle_dedupe_all` → `app/services/dedup/merge.py::dedupe_all`:

- Loads non-`MERGED` stories (newest `limit=5000`).
- Union-find over pairs within a 7-day discovery window — O(n·w), not O(n²).
- Each connected cluster is merged by `merge_cluster` → `merge_stories`.

### Merge semantics (`merge_stories`)

- Guard rails: `keep_id != absorb_id`, both must exist, neither `APPROVED` /
  `PUBLISHED` / `MERGED` — otherwise `MergeError` (HTTP 400).
- Keep is chosen by `pick_keep`: **most source links wins; tie → earliest
  discovered**.
- Absorbed story's `StorySource` links are moved to the keep story:
  - a link to a source the keep already has is **deleted** (avoids PK conflict
    and link fragmentation);
  - the absorbed story's `primary` link is demoted to `secondary` (relevance
    capped at 0.85) when the keep already has a primary.
- The absorbed story becomes a tombstone: `status = "MERGED"`,
  `url = NULL` (the column is unique), `merged_into_id = keep.id`. Slug is kept
  so old URLs still resolve.
- Keep inherits a missing `image_url` and the longer `summary`.
- An `AuditLog` row (`action = "story_merged"`) records the absorbed story's
  original title/url/summary/status in `previous_value` — the URL is never
  lost.

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/dedup/run` | Submit the `dedupe_all` job (202, poll `GET /api/v1/ingestion/jobs/{id}`). |
| POST | `/api/v1/dedup/merge` | Manually merge `{"keep_id": …, "absorb_id": …}` (400 on invalid pairs). |
| GET | `/api/v1/dedup/candidates` | Near-miss pairs scored in `[min_score, 0.85)` (default min 0.70), best first, `limit` cap — for review. |

## Dashboard

`/dashboard/stories` gained a **Run dedup** action next to Run ingestion; it
polls the shared job endpoint and reports how many clusters were merged. A
story absorbed into another shows a `MERGED` status badge.

## Testing

`tests/test_dedup_similarity.py`, `tests/test_dedup_merge.py`,
`tests/test_api_dedup.py` plus a cross-source fuzzy-match ingestion test in
`tests/test_ingestion.py`. `tests/conftest.py` registers a fake `dedupe_all`
handler for API tests.