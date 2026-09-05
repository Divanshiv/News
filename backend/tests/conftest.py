import os

os.environ["DATABASE_URL"] = "postgresql+asyncpg://localhost:5432/ai_newsroom_test"

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import Base, engine
from app.main import app


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


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client