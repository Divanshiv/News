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
| `openai.py`     | `OpenAIProvider` — OpenAI Chat Completions API |
| `anthropic.py`  | `AnthropicProvider` — Anthropic Messages API   |
| `__init__.py`   | `get_provider()` factory (env-driven)          |

`LLMProvider.generate(prompt, *, system, format, temperature, max_tokens)`
returns `LLMResponse(text, model, prompt_tokens, completion_tokens)`. Agents
call `get_provider()` to obtain the configured backend; swapping providers is a
config change, not a code change. `format` may be `"json"` or a JSON schema.

Provider notes:

- **Ollama** enforces the schema server-side (`format`), so agents never parse
  prose. Endpoint `POST {url}/api/generate`; usage from `prompt_eval_count` /
  `eval_count`; `404` (model not installed) and transport errors raise
  `LLMError`.
- **OpenAI** maps `format` to `response_format={"type": "json_object"}`, and
  works against any OpenAI-compatible endpoint via `OPENAI_BASE_URL` (Azure,
  local proxies). Usage comes from `usage.prompt_tokens` /
  `usage.completion_tokens`; `401`/`429` and transport errors raise `LLMError`.
- **Anthropic** has no `response_format`; a JSON-schema `format` appends an
  "output raw JSON only" instruction instead, and the scout's robust parser +
  rules fallback absorbs any prose. `max_tokens` is required by the Messages
  API and defaults to `ANTHROPIC_MAX_TOKENS`. Usage from
  `usage.input_tokens` / `usage.output_tokens`; `401`/`429` and transport
  errors raise `LLMError`.

Configuration (`backend/.env`):

| Variable                 | Default                      | Purpose                 |
|--------------------------|------------------------------|-------------------------|
| `LLM_PROVIDER`           | `ollama`                     | Provider selected by `get_provider()` (ollama \| openai \| anthropic) |
| `OLLAMA_URL`             | `http://localhost:11434`     | Ollama server base URL  |
| `OLLAMA_MODEL`           | `llama3.2`                   | Model name              |
| `OLLAMA_TIMEOUT_SECONDS` | `60`                         | Per-request timeout     |
| `OPENAI_API_KEY`         | *(empty)*                    | Bearer token (required for openai) |
| `OPENAI_MODEL`           | `gpt-5-mini`                 | Chat Completions model  |
| `OPENAI_BASE_URL`        | `https://api.openai.com/v1`  | Any OpenAI-compatible endpoint |
| `OPENAI_TIMEOUT_SECONDS` | `60`                         | Per-request timeout     |
| `ANTHROPIC_API_KEY`      | *(empty)*                    | `x-api-key` header (required for anthropic) |
| `ANTHROPIC_MODEL`        | `claude-sonnet-4-20250514`   | Messages API model      |
| `ANTHROPIC_BASE_URL`     | `https://api.anthropic.com`  | Messages API base URL   |
| `ANTHROPIC_MAX_TOKENS`   | `4096`                       | Required default cap    |
| `ANTHROPIC_TIMEOUT_SECONDS` | `60`                       | Per-request timeout     |

API keys are read from the environment only and never surface through the
API or to the browser — `GET /api/v1/meta/config` exposes provider/model
names but never credentials. All-provider failures fall back to the scout's
deterministic rules, so the pipeline stays runnable when a provider is
unavailable or unconfigured.

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