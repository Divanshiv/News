# Database

## Phase 2 — Core schema (current)

Async SQLAlchemy 2.0 (`SQLAlchemy[asyncio]`) + `asyncpg` + Alembic migrations.
Engine and session factory live in `backend/app/core/database.py`; the declarative
`Base` uses the `NAMING_CONVENTION` from `app/core/database.py` so every generated
constraint/index has a stable, consistent name.

Connection string (from `DATABASE_URL` in `backend/.env`, see `.env.example`):

```
postgresql+asyncpg://localhost:5432/ai_newsroom
```

## Schema overview — 14 tables across 13 entities

| Endpoint/entity      | Model file        | Notes                                             |
|----------------------|-------------------|---------------------------------------------------|
| Sources              | `models/source.py`| RSS feeds + basic metadata, `unique_slug`         |
| Stories              | `models/story.py` | Story lifecycle + scores, `unique_slug`           |
| Story–Source links   | `models/story.py` | `story_sources` M2M; composite PK, cascades       |
| Claims               | `models/claim.py` | Extracted claims with verification status         |
| Evidence             | `models/claim.py` | URLs/notes backing a claim                        |
| Research runs        | `models/research.py` | Per-story agent research runs                  |
| Articles             | `models/article.py`| SEO fields, DRAFT → PUBLISHED timestamps          |
| Social posts         | `models/social.py`| Instagram image/carousel/reel drafts              |
| Media assets         | `models/social.py`| `metadata_json` column maps to reserved `metadata`|
| Agent runs           | `models/agents.py`| Scout/Research/Verification/Writer runs           |
| Publishing jobs      | `models/agents.py`| Website + Instagram publish attempt records       |
| Users                | `models/user.py`  | Local auth; scrypt-hashed `hashed_password`       |
| Audit log            | `models/audit.py` | Append-only operator/action log                   |

### Resolved SQLAlchemy gotchas

- MediaAsset uses `metadata_json` (column `"metadata"`) — `metadata` is reserved
  by the `MetaData` API.
- StorySource uses `relationship_note` (column `"relationship"`) — a plain
  column named `relationship` shadows the `relationship()` declarative API.

### Status constants (defined in the model modules)

| Model            | Values                                                       |
|------------------|--------------------------------------------------------------|
| Story            | DISCOVERED · RESEARCHING · VERIFICATION · DRAFT · REVIEW · APPROVED · PUBLISHED · REJECTED |
| Claim            | CONFIRMED · LIKELY · UNCONFIRMED · CONTRADICTED              |
| Article          | DRAFT · REVIEW · APPROVED · PUBLISHED                        |
| ResearchRun      | PENDING · RUNNING · COMPLETED · FAILED                       |
| AgentRun         | PENDING · RUNNING · COMPLETED · FAILED                       |
| SocialPost       | platforms: instagram; types: image · carousel · reel         |

## Migrations

Alembic is configured for async (`alembic init -t async alembic`); `alembic/env.py`
imports `app.models` and reads `settings.database_url`, so migrations always target
the environment's `DATABASE_URL`.

```bash
cd backend
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
uv run alembic downgrade -1     # roll back one step
```

The initial migration is `alembic/versions/1851973ad4c4_create_core_tables.py`.

## Seed data

Idempotent seed (safe to re-run) — creates the admin operator and a default set
of RSS sources:

```bash
cd backend
uv run python -m scripts.seed
```

| Item            | Value                             |
|-----------------|-----------------------------------|
| Admin email     | `admin@ainewsroom.local`          |
| Admin password  | `admin123`                        |
| Sources         | 10 (Ars Technica, BleepingComputer, …) |

## Testing

Tests run against a separate database (`ai_newsroom_test`) so dev data is never
touched. `backend/tests/conftest.py` forces `DATABASE_URL` to the test database,
drops/creates all tables per test (autouse fixture), and exposes an async
`httpx.AsyncClient` via an ASGI transport. The shared engine pool is disposed
after each test because pytest-asyncio runs each test in a fresh event loop and
asyncpg connections are loop-bound.

```bash
cd backend
uv run pytest          # 26 tests: health + sources + stories + articles CRUD
```