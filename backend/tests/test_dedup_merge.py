from sqlalchemy import func, select

import pytest

from app.core.database import async_session_factory
from app.models.audit import AuditLog
from app.models.source import Source
from app.models.story import Story, StorySource
from app.services.dedup.merge import MergeError, merge_stories


async def _make_source(**overrides) -> Source:
    data = {
        "name": "Example News",
        "url": "https://example.com",
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


async def _make_story(
    source: Source, title: str, note: str = "primary", url: str | None = None
) -> Story:
    async with async_session_factory() as session:
        story = Story(
            title=title,
            slug=title.lower().replace(" ", "-"),
            url=url,
            category="Technology",
            status="DISCOVERED",
            summary="A reasonably long summary describing the news event in detail.",
        )
        session.add(story)
        await session.flush()
        session.add(
            StorySource(
                story_id=story.id,
                source_id=source.id,
                relationship_note=note,
                relevance_score=1.0 if note == "primary" else 0.9,
            )
        )
        await session.commit()
        await session.refresh(story)
        return story


async def _add_link(
    story_id: int, source: Source, note: str = "secondary", relevance: float = 0.9
):
    async with async_session_factory() as session:
        session.add(
            StorySource(
                story_id=story_id,
                source_id=source.id,
                relationship_note=note,
                relevance_score=relevance,
            )
        )
        await session.commit()


async def _links(story_id: int) -> list[StorySource]:
    async with async_session_factory() as session:
        rows = (
            await session.execute(select(StorySource).where(StorySource.story_id == story_id))
        ).scalars().all()
        return rows


@pytest.mark.asyncio
async def test_merge_moves_links_and_marks_absorbed():
    src1 = await _make_source(name="One")
    src2 = await _make_source(name="Two")
    src3 = await _make_source(name="Three")
    keep = await _make_story(src1, "Keep story title", url="http://example.com/keep")
    absorb = await _make_story(
        src2, "Keep story title variant", url="http://example.com/absorbed"
    )
    await _add_link(absorb.id, src3, note="secondary", relevance=0.9)

    async with async_session_factory() as session:
        report = await merge_stories(session, keep.id, absorb.id)

    assert report["keep_id"] == keep.id
    assert report["absorbed_id"] == absorb.id
    assert report["moved_links"] == 2

    async with async_session_factory() as session:
        stored = await session.get(Story, absorb.id)
        assert stored.status == "MERGED"
        assert stored.url is None

    keep_links = await _links(keep.id)
    assert {link.source_id for link in keep_links} == {src1.id, src2.id, src3.id}
    assert any(link.relationship_note == "primary" for link in keep_links)


@pytest.mark.asyncio
async def test_merge_same_source_link_deleted_and_url_preserved_in_audit():
    src1 = await _make_source(name="One")
    src2 = await _make_source(name="Two")
    keep = await _make_story(src1, "Story one title", url="http://example.com/keep")
    absorb = await _make_story(
        src1, "Story one title duplicate", url="http://example.com/dupe"
    )
    await _add_link(absorb.id, src2)

    async with async_session_factory() as session:
        await merge_stories(session, keep.id, absorb.id)

    async with async_session_factory() as session:
        count = (
            await session.execute(
                select(func.count())
                .select_from(StorySource)
                .where(StorySource.source_id == src1.id)
            )
        ).scalar_one()
        assert count == 1

    async with async_session_factory() as session:
        audit = (
            await session.execute(
                select(AuditLog).where(
                    AuditLog.action == "story_merged",
                    AuditLog.entity_id == str(absorb.id),
                )
            )
        ).scalar_one()
        assert audit.previous_value["url"] == "http://example.com/dupe"
        assert audit.previous_value["title"] == "Story one title duplicate"


@pytest.mark.asyncio
async def test_merge_into_self_raises():
    src = await _make_source(name="One")
    story = await _make_story(src, "Title", url="http://example.com/story")
    async with async_session_factory() as session:
        with pytest.raises(MergeError):
            await merge_stories(session, story.id, story.id)


@pytest.mark.asyncio
async def test_merge_missing_story_raises():
    src = await _make_source(name="One")
    keep = await _make_story(src, "Title one", url="http://example.com/keep")
    async with async_session_factory() as session:
        with pytest.raises(MergeError):
            await merge_stories(session, keep.id, 9999)