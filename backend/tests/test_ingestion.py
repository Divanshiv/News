from sqlalchemy import func, select

from app.core.database import async_session_factory
from app.models.source import Source
from app.models.story import Story, StorySource
from app.services.ingestion import IngestionService
from app.services.rss.fetch import RSSFetchError
from tests.feed_fixtures import DUPLICATE_TITLE_FEED_XML, RSS_FEED_XML


class FakeFetcher:
    def __init__(self, responses: dict[str, bytes | Exception] | None = None):
        self._responses = responses or {}

    async def fetch(self, url: str) -> bytes:
        response = self._responses.get(url)
        if isinstance(response, Exception):
            raise response
        return response or b""


async def _count(model) -> int:
    async with async_session_factory() as session:
        return await session.scalar(select(func.count()).select_from(model))


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


def _service(payload: bytes):
    return IngestionService(
        fetcher=FakeFetcher({"https://example.com/feed.xml": payload})
    )


class TestIngestSource:
    async def test_creates_stories_and_links_source(self):
        source = await _create_source()
        result = await _service(RSS_FEED_XML.encode()).ingest_source(source)

        assert result.status == "ok"
        assert result.fetched == 4
        assert result.created == 4
        assert result.skipped == 0
        assert await _count(Story) == 4

        async with async_session_factory() as session:
            stories = (await session.execute(select(Story).order_by(Story.id))).scalars().all()
            assert stories[0].title == "Alpha emerges from stealth with new chip"
            assert stories[0].url == "https://example.com/stories/alpha-chip"
            assert stories[0].summary == "Alpha announced a new processor today."
            assert stories[0].author == "editor@example.com (Jane Doe)"
            assert stories[0].source_published_at is not None
            assert stories[0].image_url == "https://example.com/img/alpha.jpg"
            assert stories[0].category == "Technology"
            assert stories[0].status == "DISCOVERED"
            link = await session.scalar(select(StorySource))
            assert link.story_id == stories[0].id
            assert link.source_id == source.id
            assert link.relationship_note == "primary"

        async with async_session_factory() as session:
            stored = await session.get(Source, source.id)
            assert stored.last_fetched_at is not None
            assert stored.last_fetch_error is None

    async def test_dedupes_by_canonical_url_on_second_run(self):
        source = await _create_source()
        service = _service(RSS_FEED_XML.encode())
        first = await service.ingest_source(source)
        second = await service.ingest_source(source)

        assert first.created == 4
        assert second.created == 0
        assert second.skipped == 4
        assert await _count(Story) == 4

    async def test_dedupes_by_normalized_title_within_same_source(self):
        source = await _create_source()
        result = await _service(DUPLICATE_TITLE_FEED_XML.encode()).ingest_source(source)

        assert result.fetched == 2
        assert result.created == 1
        assert result.skipped == 1
        assert await _count(Story) == 1
        async with async_session_factory() as session:
            links = (await session.execute(select(StorySource))).scalars().all()
            assert len(links) == 1

    async def test_cross_source_fuzzy_match_links_not_duplicates(self):
        first_source = await _create_source(name="First News", rss_url="https://one.example.com/feed")
        second_source = await _create_source(name="Second News", rss_url="https://two.example.com/feed")

        feed_a = RSS_FEED_XML.encode()
        second_feed_xml = RSS_FEED_XML.replace(
            "https://example.com/feed.xml", "https://two.example.com/feed"
        ).replace(
            "https://example.com/stories/", "https://two.example.com/stories/"
        ).replace(
            "Alpha emerges from stealth with new chip",
            "Alpha emerges from stealth with a new chip today",
        )
        feed_b = second_feed_xml.encode()

        fetcher = FakeFetcher(
            {
                "https://one.example.com/feed": feed_a,
                "https://two.example.com/feed": feed_b,
            }
        )
        service = IngestionService(fetcher=fetcher)
        await service.ingest_source(first_source)

        async with async_session_factory() as session:
            before = await session.scalar(
                select(Story).where(Story.title == "Alpha emerges from stealth with new chip")
            )
            assert before is not None
            before_id = before.id

        second_result = await service.ingest_source(second_source)

        assert second_result.created == 0
        assert second_result.skipped == 4
        async with async_session_factory() as session:
            dupe = await session.scalar(
                select(Story).where(Story.title == "Alpha emerges from stealth with new chip")
            )
            assert dupe.id == before_id
            alphas = (
                await session.execute(
                    select(StorySource).where(StorySource.story_id == before_id)
                )
            ).scalars().all()
            assert {link.source_id for link in alphas} == {first_source.id, second_source.id}
            assert await _count(Story) == 4

    async def test_marks_source_with_fetch_error_and_creates_no_stories(self):
        source = await _create_source()
        failing = IngestionService(
            fetcher=FakeFetcher({"https://example.com/feed.xml": RSSFetchError("boom")})
        )
        result = await failing.ingest_source(source)

        assert result.status == "error"
        assert result.error == "boom"
        assert result.fetched == 0
        assert await _count(Story) == 0
        async with async_session_factory() as session:
            stored = await session.get(Source, source.id)
            assert stored.last_fetched_at is not None
            assert "boom" in stored.last_fetch_error


class TestIngestAll:
    async def test_processes_each_active_source_separately(self):
        good = await _create_source(name="Good News")
        await _create_source(name="Broken News", rss_url="https://broken.example.com/feed")
        failing = IngestionService(
            fetcher=FakeFetcher(
                {
                    "https://example.com/feed.xml": RSS_FEED_XML.encode(),
                    "https://broken.example.com/feed": RSSFetchError("network down"),
                }
            )
        )
        results = await failing.ingest_all()

        assert len(results) == 2
        by_name = {r.source_name: r for r in results}
        assert by_name["Good News"].status == "ok"
        assert by_name["Broken News"].status == "error"
        assert by_name["Broken News"].error == "network down"

    async def test_ignores_inactive_and_rssless_sources(self):
        await _create_source(name="Inactive", active=False)
        await _create_source(name="No Feed", rss_url=None)
        results = await _service(RSS_FEED_XML.encode()).ingest_all()
        assert results == []