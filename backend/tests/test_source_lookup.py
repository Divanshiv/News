from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.source import Source
from app.models.story import Story, StorySource
from app.tools.source_lookup import (
    SourceLookupTool,
    domain_of,
    normalize_research_url,
    tier_for_url,
)


def test_domain_of_strips_www_and_scheme():
    assert domain_of("https://www.Example.com/path?q=1") == "example.com"
    assert domain_of("http://news.gov.in/x") == "news.gov.in"


def test_normalize_research_url_drops_tracking_params():
    url = "https://example.com/a?utm_source=x&utm_medium=y&id=42&ref=z"
    normalized = normalize_research_url(url)
    assert "utm_source" not in normalized
    assert "id=42" in normalized
    assert normalize_research_url("https://a.com/b#frag") == "https://a.com/b"


def test_tier_for_url_classifies_primary_and_social():
    assert tier_for_url("https://www.nasa.gov/news/1") == "primary"
    assert tier_for_url("https://example.gov.in") == "primary"
    assert tier_for_url("https://x.com/elonmusk/status/1") == "social"
    assert tier_for_url("https://reuters.com/world") == "news"
    assert tier_for_url("https://reuters.com/world", source_type="official") == "primary"


async def test_get_or_create_creates_and_reuses_source():
    async with async_session_factory() as session:
        lookup = SourceLookupTool(session)
        first = await lookup.get_or_create(
            url="https://acme.com/press?id=1&utm_source=t", name="ACME", category="AI"
        )
        assert first is not None
        assert first.name == "ACME"
        assert "utm_source" not in first.url

        second = await lookup.get_or_create(
            url="https://acme.com/press?id=1&utm_source=t", name="ACME", category="AI"
        )
        assert second.id == first.id
        session.expunge_all()


async def test_source_lookup_links_story_source():
    async with async_session_factory() as session:
        story = Story(title="Test story", slug="lookup-story", status="DISCOVERED")
        session.add(story)
        await session.commit()

        lookup = SourceLookupTool(session)
        source = await lookup.get_or_create(
            url="https://example.org/research", name="Example Org"
        )
        session.add(
            StorySource(
                story_id=story.id,
                source_id=source.id,
                relationship_note="research (news)",
                relevance_score=0.9,
            )
        )
        await session.commit()

        rows = (
            await session.execute(
                select(StorySource).where(StorySource.story_id == story.id)
            )
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].source_id == source.id
        session.expunge_all()