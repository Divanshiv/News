from app.core.database import async_session_factory
from app.models.source import Source
from app.models.story import StorySource


async def _create_source(name="Example News") -> Source:
    async with async_session_factory() as session:
        source = Source(
            name=name,
            url="https://example.com",
            source_type="news",
            category="Technology",
            reliability_score=0.8,
            active=True,
        )
        session.add(source)
        await session.commit()
        await session.refresh(source)
        return source


async def _create_story(title, source_id, url=None, status="DISCOVERED"):
    from app.models.story import Story

    async with async_session_factory() as session:
        story = Story(
            title=title,
            slug=title.lower().replace(" ", "-"),
            url=url,
            category="Technology",
            status=status,
            summary="A reasonably long summary describing this news event in enough detail.",
        )
        session.add(story)
        await session.flush()
        session.add(StorySource(story_id=story.id, source_id=source_id, relationship_note="primary"))
        await session.commit()
        await session.refresh(story)
        return story


async def test_run_dedupe_returns_job(client):
    response = await client.post("/api/v1/dedup/run")
    assert response.status_code == 202
    data = response.json()
    assert data["job_name"] == "dedupe_all"
    assert data["status"] == "QUEUED"


async def test_merge_two_stories(client):
    source = await _create_source()
    keep = await _create_story("Keep event title", source.id, url="http://example.com/keep")
    absorb = await _create_story(
        "Keep event title variant", source.id, url="http://example.com/absorb"
    )
    response = await client.post(
        "/api/v1/dedup/merge",
        json={"keep_id": keep.id, "absorb_id": absorb.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["absorbed_id"] == absorb.id
    assert data["moved_links"] == 0


async def test_merge_self_rejected(client):
    source = await _create_source()
    story = await _create_story("A story", source.id, url="http://example.com/a")
    response = await client.post(
        "/api/v1/dedup/merge",
        json={"keep_id": story.id, "absorb_id": story.id},
    )
    assert response.status_code == 400


async def test_merge_missing_rejected(client):
    source = await _create_source()
    keep = await _create_story("Keep title", source.id, url="http://example.com/keep")
    response = await client.post(
        "/api/v1/dedup/merge",
        json={"keep_id": keep.id, "absorb_id": 9999},
    )
    assert response.status_code == 400


async def test_candidates_returns_near_matches(client):
    source = await _create_source()
    await _create_story("Alpha raises funding round", source.id, url="http://example.com/a")
    await _create_story("Alpha raises funding round more", source.id, url="http://example.com/b")
    response = await client.get("/api/v1/dedup/candidates")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)