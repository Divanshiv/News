import asyncio
from datetime import datetime, timezone

from app.core.database import async_session_factory
from app.models.claim import Claim
from app.models.research import ResearchRun
from app.models.source import Source
from app.models.story import Story, StorySource


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
            title="Research me",
            slug="research-me",
            url="https://example.com/research-me",
            status="DISCOVERED",
            should_research=True,
            discovered_at=datetime.now(timezone.utc),
        )
        session.add(story)
        await session.commit()
        await session.refresh(story)
        return story.id


async def test_run_research_endpoint_returns_job(client):
    response = await client.post("/api/v1/research/run")
    assert response.status_code == 202
    body = response.json()
    assert body["job_name"] == "research_story"
    assert body["status"] == "QUEUED"

    job = await _poll_until_completed(client, body["job_id"])
    assert job["status"] == "COMPLETED"


async def test_research_story_endpoint(client):
    story_id = await _seed_story()
    response = await client.post(f"/api/v1/research/stories/{story_id}")
    assert response.status_code == 202
    body = response.json()
    assert body["job_name"] == "research_story"

    job = await _poll_until_completed(client, body["job_id"])
    assert job["status"] == "COMPLETED"


async def test_research_story_unknown_returns_404(client):
    response = await client.post("/api/v1/research/stories/99999")
    assert response.status_code == 404


async def test_get_story_research_empty(client):
    story_id = await _seed_story()
    response = await client.get(f"/api/v1/research/runs/{story_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["story_id"] == story_id
    assert body["runs"] == []
    assert body["claims"] == []
    assert body["sources"] == []


async def test_get_story_research_unknown_returns_404(client):
    response = await client.get("/api/v1/research/runs/99999")
    assert response.status_code == 404


async def test_get_story_research_includes_persisted_data(client):
    story_id = await _seed_story()
    async with async_session_factory() as session:
        session.add(
            ResearchRun(
                story_id=story_id,
                agent_name="research",
                status="COMPLETED",
                input={"title": "t"},
                output={"sources": [{"url": "https://a.com"}]},
            )
        )
        source = Source(name="ACME", url="https://acme.com", source_type="news")
        session.add(source)
        await session.flush()
        session.add(
            StorySource(
                story_id=story_id,
                source_id=source.id,
                relationship_note="research (news)",
                relevance_score=0.8,
            )
        )
        claim = Claim(story_id=story_id, claim_text="ACME announced product Y.")
        session.add(claim)
        await session.commit()
        claim_id = claim.id

    response = await client.get(f"/api/v1/research/runs/{story_id}")
    assert response.status_code == 200
    body = response.json()
    assert len(body["runs"]) == 1
    assert body["runs"][0]["status"] == "COMPLETED"
    assert len(body["sources"]) == 1
    assert body["sources"][0]["name"] == "ACME"
    assert body["claims"][0]["id"] == claim_id
    assert body["claims"][0]["status"] == "UNCONFIRMED"