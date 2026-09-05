import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.articles import router as articles_router
from app.api.dedup import router as dedup_router
from app.api.health import router as health_router
from app.api.ingestion import router as ingestion_router
from app.api.jobs import router as jobs_router
from app.api.meta import router as meta_router
from app.api.scout import router as scout_router
from app.api.sources import router as sources_router
from app.api.stories import router as stories_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.workers import dedup as _dedup  # noqa: F401  registers job handlers on the shared runner
from app.workers import ingestion as _ingestion  # noqa: F401  registers job handlers on the shared runner
from app.workers import scout as _scout  # noqa: F401  registers job handlers on the shared runner
from app.workers.jobs import job_runner

logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    job_runner.start()
    logger.info("application starting", extra={"environment": settings.environment})
    yield
    job_runner.shutdown()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix=settings.api_v1_prefix)
app.include_router(sources_router, prefix=f"{settings.api_v1_prefix}/sources")
app.include_router(stories_router, prefix=f"{settings.api_v1_prefix}/stories")
app.include_router(articles_router, prefix=f"{settings.api_v1_prefix}/articles")
app.include_router(ingestion_router, prefix=f"{settings.api_v1_prefix}/ingestion")
app.include_router(jobs_router, prefix=f"{settings.api_v1_prefix}/jobs")
app.include_router(meta_router, prefix=f"{settings.api_v1_prefix}/meta")
app.include_router(dedup_router, prefix=f"{settings.api_v1_prefix}/dedup")
app.include_router(scout_router, prefix=f"{settings.api_v1_prefix}/scout")


@app.get("/")
async def root():
    return {
        "service": "ai-newsroom-backend",
        "version": settings.app_version,
        "docs": "/docs",
        "health": f"{settings.api_v1_prefix}/health",
    }