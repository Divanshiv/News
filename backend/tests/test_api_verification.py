import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_run_verification_returns_job(client):
    resp = await client.post("/api/v1/verification/run")
    assert resp.status_code == 202
    body = resp.json()
    assert "job_id" in body
    assert body["job_name"] == "verify_story"


async def test_verify_story_not_found(client):
    resp = await client.post("/api/v1/verification/stories/99999")
    assert resp.status_code == 404


async def test_get_verification_not_found(client):
    resp = await client.get("/api/v1/verification/stories/99999")
    assert resp.status_code == 404


async def test_update_claim_not_found(client):
    resp = await client.patch("/api/v1/verification/claims/99999", json={"status": "CONFIRMED"})
    assert resp.status_code == 404
