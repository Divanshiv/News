import asyncio
import time

from app.core.database import async_session_factory
from app.models.source import Source


async def _run_job(client, job_id: str, timeout: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout
    job = {}
    while time.monotonic() < deadline:
        resp = await client.get(f"/api/v1/ingestion/jobs/{job_id}")
        assert resp.status_code == 200
        job = resp.json()
        if job["status"] in ("COMPLETED", "FAILED"):
            return job
        await asyncio.sleep(0.02)
    return job


async def _create_source(**overrides) -> Source:
    data = {
        "name": "Example News",
        "url": "https://example.com",
        "rss_url": "https://example.com/feed.xml",
        "source_type": "news",
        "category": "Technology",
        "reliability_score": 0.8,
        "active": True,
    }
    data.update(overrides)
    async with async_session_factory() as session:
        source = Source(**data)
        session.add(source)
        await session.commit()
        await session.refresh(source)
        return source


class TestRunIngestion:
    async def test_run_submits_job_and_completes(self, client):
        resp = await client.post("/api/v1/ingestion/run")
        assert resp.status_code == 202
        body = resp.json()
        assert body["job_name"] == "ingest_all"
        assert body["status"] in ("QUEUED", "RUNNING")
        assert body["job_id"]

        job = await _run_job(client, body["job_id"])
        assert job["status"] == "COMPLETED"
        assert job["error"] is None
        assert job["created_at"] is not None
        assert job["completed_at"] is not None
        assert job["result"] == [
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


class TestFetchSource:
    async def test_fetch_existing_source(self, client):
        source = await _create_source()
        resp = await client.post(f"/api/v1/ingestion/sources/{source.id}/fetch")
        assert resp.status_code == 202
        body = resp.json()
        assert body["job_name"] == "ingest_source"

        job = await _run_job(client, body["job_id"])
        assert job["status"] == "COMPLETED"
        assert job["result"][0]["source_id"] == source.id
        assert job["result"][0]["status"] == "ok"

    async def test_fetch_unknown_source_returns_404(self, client):
        resp = await client.post("/api/v1/ingestion/sources/9999/fetch")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Source not found"

    async def test_fetch_source_without_rss_url_returns_400(self, client):
        source = await _create_source(rss_url=None)
        resp = await client.post(f"/api/v1/ingestion/sources/{source.id}/fetch")
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Source has no RSS URL configured"


class TestGetJob:
    async def test_unknown_job_returns_404(self, client):
        resp = await client.get("/api/v1/ingestion/jobs/nope")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Job not found"

    async def test_dedupe_job_result_with_merge_clusters_serializes(self, client):
        resp = await client.post("/api/v1/dedup/run")
        assert resp.status_code == 202

        job = await _run_job(client, resp.json()["job_id"])
        assert job["status"] == "COMPLETED"
        assert job["result"] == [
            {"keep_id": 1, "absorbed_ids": [2], "moved_links": 1}
        ]