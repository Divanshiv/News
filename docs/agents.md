# Agents

Agents are the AI workers of the newsroom. Each agent takes structured input,
produces structured output, and depends on an LLM provider — never on a
concrete model or server.

## LLM provider layer

`app/services/llm/` defines the provider contract (spec §22):

| File            | Purpose                                        |
|-----------------|------------------------------------------------|
| `base.py`       | `LLMProvider` ABC + `LLMResponse` + `LLMError` |
| `ollama.py`     | `OllamaProvider` — local Ollama REST API        |
| `__init__.py`   | `get_provider()` factory (env-driven)          |

`LLMProvider.generate(prompt, *, system, format, temperature, max_tokens)`
returns `LLMResponse(text, model, prompt_tokens, completion_tokens)`. Agents
call `get_provider()` to obtain the configured backend; swapping providers is a
config change, not a code change. `format` may be `"json"` or a JSON schema —
Ollama enforces it server-side so agents never parse prose.

Ollama details:

- Endpoint: `POST {url}/api/generate` (stream off)
- `options.temperature` and `options.num_predict` forwarded when provided
- Usage counters: `prompt_eval_count` and `eval_count`
- `404` (model not installed) and transport errors raise `LLMError`

Configuration (`backend/.env`):

| Variable                | Default                 | Purpose                 |
|-------------------------|-------------------------|-------------------------|
| `LLM_PROVIDER`          | `ollama`                | Provider selected by `get_provider()` |
| `OLLAMA_URL`            | `http://localhost:11434`| Ollama server base URL  |
| `OLLAMA_MODEL`          | `llama3.2`              | Model name              |
| `OLLAMA_TIMEOUT_SECONDS`| `60`                    | Per-request timeout     |

## Scout agent

`app/agents/scout.py` — the first production agent (Phase 5). It grades a
single story and emits a `ScoutVerdict`:

```json
{
  "should_research": true,
  "importance": 7,
  "category": "AI",
  "reason": "Significant model release."
}
```

The verdict is enforced by a JSON schema sent via `format`, so output is valid
by construction. The agent:

1. Builds a prompt from title/summary/source category/publication date.
2. Calls the provider with a strict system prompt and low temperature.
3. Parses the JSON robustly (strips fenced/prose-wrapped output, coerces
   category to the fixed `SOURCE_CATEGORIES` set).
4. Retries once on provider or parse failure (`DEFAULT_MAX_RETRIES = 1`).
5. Falls back to deterministic keyword rules when the LLM is unavailable, so
   the app stays runnable and free locally (importance 4 default; funding →
   8, breaches → 9, etc.; `should_research = importance >= 6`; category from
   keyword votes or the source hint).

## Execution

`workers/scout.py` registers the `run_scout` job. It scores the oldest
unscouted `DISCOVERED` stories (batch 50, one per run) or a single story via
`{"story_id": id}`. Results are written in place on the story — `category`,
`importance_score`, `should_research`, `scout_reason`, `scouted_at` — and
returned as a per-story report. Already-scouted stories are skipped
(`should_research IS NULL` is the pending filter), and a failing story is
isolated so the run continues.

## API

| Method | Path                        | Behavior                        |
|--------|-----------------------------|---------------------------------|
| POST   | `/api/v1/scout/run`         | 202 → `run_scout` job, batch    |
| POST   | `/api/v1/scout/stories/{id}`| 202 → `run_scout` job, single   |

Jobs run on the shared in-process runner and are polled via
`GET /api/v1/ingestion/jobs/{id}` (§24).

## Testing

Providers are tested with `httpx.MockTransport`; agents with a fake provider
that replays canned responses/exceptions. The `run_scout` job is faked in
`tests/conftest.py` for API tests; worker tests run the real handler against
the test database with a fake provider.