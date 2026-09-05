import asyncio
from datetime import datetime, timezone

from app.core.database import async_session_factory
from app.models.story import Story


async def _poll_until_completed(client, job_id: str, attempts: int = 20):
    for _ in range(attempts):
        response = await client.get(f"/api/v1/ingestion/jobs/{job_id}")
        assert response.status_code == 200
        body = response.json()
        if body["status"] in {"COMPLETED", "FAILED"}:
            return body
        await asyncio.sleep(0.01)
    raise AssertionError("job did not complete in time")


async def _seed_story() -> int:
    async with async_session_factory() as session:
        story = Story(
            title="Scout me",
            slug="scout-me",
            url="https://example.com/scout",
            status="DISCOVERED",
            discovered_at=datetime.now(timezone.utc),
        )
        session.add(story)
        await session.commit()
        await session.refresh(story)
        return story.id


async def test_run_scout_endpoint_returns_job(client):
    response = await client.post("/api/v1/scout/run")
    assert response.status_code == 202
    body = response.json()
    assert body["job_name"] == "run_scout"
    assert body["status"] == "QUEUED"

    job = await _poll_until_completed(client, body["job_id"])
    assert job["status"] == "COMPLETED"
    assert job["result"][0]["should_research"] is True


async def test_scout_story_endpoint(client):
    story_id = await _seed_story()
    response = await client.post(f"/api/v1/scout/stories/{story_id}")
    assert response.status_code == 202
    body = response.json()
    assert body["job_name"] == "run_scout"

    job = await _poll_until_completed(client, body["job_id"])
    assert job["status"] == "COMPLETED"


async def test_scout_story_unknown_returns_404(client):
    response = await client.post("/api/v1/scout/stories/99999")
    assert response.status_code == 404


async def test_story_read_exposes_scout_fields(client):
    async with async_session_factory() as session:
        story = Story(
            title="Scouted story",
            slug="scouted-story",
            url="https://example.com/scouted",
            status="DISCOVERED",
            should_research=True,
            importance_score=7.5,
            category="AI",
            scout_reason="Significant release.",
            discovered_at=datetime.now(timezone.utc),
        )
        session.add(story)
        await session.commit()
        story_id = story.id
    response = await client.get(f"/api/v1/stories/{story_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["should_research"] is True
    assert body["scout_reason"] == "Significant release."