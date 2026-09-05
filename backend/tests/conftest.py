import os

os.environ["DATABASE_URL"] = "postgresql+asyncpg://localhost:5432/ai_newsroom_test"

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import Base, engine
from app.main import app
from app.workers.jobs import job_runner


@pytest.fixture(autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Ensure the pool is not reused across test loops (pytest-asyncio
    # creates a fresh event loop per test; asyncpg connections are
    # bound to the loop that created them).
    await engine.dispose()


@pytest.fixture(autouse=True)
def isolated_job_runner():
    job_runner.reset()
    job_runner.register("ingest_all", fake_ingest_all)
    job_runner.register("ingest_source", fake_ingest_source)
    yield
    job_runner.reset()


async def fake_ingest_all(payload: dict) -> list[dict]:
    return [
        {
            "source_id": 1,
            "source_name": "Example News",
            "status": "ok",
            "fetched": 4,
            "created": 4,
            "skipped": 0,
            "error": None,
        }
    ]


async def fake_ingest_source(payload: dict) -> dict:
    return {
        "source_id": payload["source_id"],
        "source_name": "Example News",
        "status": "ok",
        "fetched": 4,
        "created": 4,
        "skipped": 0,
        "error": None,
    }


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client