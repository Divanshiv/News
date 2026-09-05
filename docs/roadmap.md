# Roadmap

Development is strictly phased. Each phase ends with acceptance criteria met,
tests green, and the app runnable locally.

| Phase | Scope | Acceptance | Status |
|-------|-------|------------|--------|
| 1 Foundation | Repo, frontend, FastAPI backend, PostgreSQL, env, health endpoint, dashboard shell | Frontend runs, backend runs, database connects | ✅ |
| 2 Database | ORM models, migrations, CRUD APIs, seed data | CRUD works for Source, Story, Article | ✅ |
| 3 RSS | Source registry, feed fetcher/parser/normalizer, ingestion job | New RSS items appear in dashboard | ✅ `docs/ingestion.md` |
| 4 Deduplication | Title/description similarity, story merging, cross-source dedup | One event = one story with multiple sources | ⏳ (canonical-URL + same-source title dedup landed in P3) |
| 5 Scout agent | LLM provider interface, Ollama provider, structured scoring | Stories get category/importance/should_research | |
| 6 Research | Web search + URL fetch tools, ResearchAgent, source collection | Story produces a research package | |
| 7 Verification | Claim + Evidence models, ClaimExtractor, VerificationAgent | Claims show status/confidence/evidence/contradictions | |
| 8 Writing | WriterAgent, article generation, article edit UI | Verified research produces editable draft | |
| 9 Website | Home/category/article/search pages, SEO, sitemap, RSS | Approved article becomes public | |
| 10 Instagram | Caption + carousel generators, graphic templates, manual export first | Approved article → Instagram-ready content | |
| 11 Approval + publishing | Review/Approve/Reject/Publish, publishing jobs | Full workflow from one dashboard | |
| 12 RAG | pgvector embeddings, semantic search, related stories | Research gets historical context | |

## Guiding constraints

- Free/open-source first; local AI (Ollama) before paid providers.
- AI providers are abstracted — agents never call provider-specific code.
- No auto-publishing of unverified AI content.
- Track token usage and agent runs; cache results; avoid re-researching.