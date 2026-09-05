# Architecture

## Phase 1 — Foundation (current)

The repository is a monorepo with three top-level components:

```
News/
├── frontend/    Next.js + TypeScript + Tailwind + shadcn/ui (public site + admin dashboard)
├── backend/     Python + FastAPI + SQLAlchemy (async) + PostgreSQL
├── docs/        Architecture, database, agent, and workflow documentation
├── scripts/     Developer helper scripts
└── docker/      Docker artifacts (compose lives at repo root)
```

### Runtime layout

```
Browser
  │
  ├── :3000  Next.js (public website + /dashboard)
  │              └── /api/* rewrites proxied to backend in dev
  └── :8000  FastAPI (REST API, /api/v1/*)
                 └── PostgreSQL :5432 (asyncpg)
```

### Backend layer map (Phase 1 scope)

| Layer      | Path            | Responsibility                          |
|------------|-----------------|-----------------------------------------|
| API        | `app/api/`      | HTTP routers (health)                   |
| Core       | `app/core/`     | Settings, DB engine/session, logging    |
| Models     | `app/models/`   | SQLAlchemy ORM models (Phase 2)         |
| Schemas    | `app/schemas/`  | Pydantic request/response models (P2)   |
| Services   | `app/services/` | Domain services (ingestion etc., P2+)   |
| Agents     | `app/agents/`   | Scout/Research/Verification/Writer (P5+)|
| Tools      | `app/tools/`    | WebSearch/URLFetch/RSSFetch (P6+)       |
| Workers    | `app/workers/`  | Background job runners (P3+)            |

### Frontend layer map

| Path                    | Purpose                              |
|-------------------------|--------------------------------------|
| `app/`                  | App Router pages (public + dashboard)|
| `components/`           | React components (`ui/` = shadcn)    |
| `lib/api.ts`            | Typed backend API client             |
| `hooks/`                | Client-side hooks (Phase 2+)         |
| `types/`                | Shared TypeScript types              |

### Configuration & secrets

- All configuration is read from the environment (see `.env.example`).
- Backend uses `pydantic-settings`; unknown env vars are ignored.
- Secrets are never committed and never shipped to the browser.
- CORS is restricted to configured origins only.

### Development flow

```
npm run dev  (frontend, :3000)
uvicorn app.main:app --reload  (backend, :8000)
postgres (local Homebrew :5432 or `docker compose up db`)
```

### Planned evolution

See `docs/roadmap.md` for the phased plan (RSS ingestion, deduplication,
scout/research/verification agents, articles, Instagram, RAG).