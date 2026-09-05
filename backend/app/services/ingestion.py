"""Feed ingestion pipeline: fetch → parse → normalize → dedupe → save Story."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import async_session_factory
from app.models.source import Source
from app.models.story import Story, StorySource
from app.services.dedup.similarity import is_same_event, pair_score
from app.services.rss.fetch import RSSFetcher, RSSFetchError
from app.services.rss.normalize import canonicalize_url, normalize_title
from app.services.rss.parse import FeedItem, ParsedFeed, parse_feed
from app.services.slugs import unique_slug
from app.tools.text_extraction import TextExtractionError, TextExtractionTool

logger = logging.getLogger(__name__)

DUPLICATE_WINDOW_DAYS = 7
FUZZY_CANDIDATE_LIMIT = 300


@dataclass
class SourceIngestResult:
    source_id: int
    source_name: str
    status: str
    fetched: int = 0
    created: int = 0
    skipped: int = 0
    error: str | None = None
    details: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "status": self.status,
            "fetched": self.fetched,
            "created": self.created,
            "skipped": self.skipped,
            "error": self.error,
        }


class IngestionService:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession] = async_session_factory,
        fetcher: RSSFetcher | None = None,
        text_extractor: TextExtractionTool | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._fetcher = fetcher or RSSFetcher()
        self._text_extractor = text_extractor or TextExtractionTool()

    async def get_source(self, source_id: int) -> Source | None:
        async with self._session_factory() as session:
            return await session.get(Source, source_id)

    async def ingest_all(self) -> list[SourceIngestResult]:
        async with self._session_factory() as session:
            sources = (
                await session.execute(
                    select(Source)
                    .where(Source.active.is_(True), Source.rss_url.is_not(None))
                    .order_by(Source.name)
                )
            ).scalars().all()
        results = [await self.ingest_source(source) for source in sources]
        return results

    async def ingest_source(self, source: Source) -> SourceIngestResult:
        result = SourceIngestResult(
            source_id=source.id, source_name=source.name, status="ok"
        )
        try:
            xml = await self._fetcher.fetch(source.rss_url)
        except RSSFetchError as exc:
            await self._record_fetch_failure(source, str(exc))
            result.status = "error"
            result.error = str(exc)
            return result

        feed = parse_feed(xml, source.rss_url)
        if feed.error and not feed.items:
            await self._record_fetch_failure(source, feed.error)
            result.status = "error"
            result.error = feed.error
            return result

        result.fetched = len(feed.items)
        async with self._session_factory() as session:
            for item in feed.items:
                outcome = await self._ingest_item(session, source, item)
                result.details.append(outcome)
                if outcome["created"]:
                    result.created += 1
                else:
                    result.skipped += 1
            source = await session.get(Source, source.id)
            if source is not None:
                source.last_fetched_at = datetime.now(timezone.utc)
                source.last_fetch_error = None
            await session.commit()
        return result

    async def _ingest_item(
        self, session: AsyncSession, source: Source, item: FeedItem
    ) -> dict:
        canonical = canonicalize_url(item.url)
        if canonical is None:
            return {"title": item.title, "created": False, "reason": "invalid_url"}
        match = await self._find_match(session, source, item, canonical)
        if match is not None:
            await self._link_if_missing(session, match, source)
            return {"title": item.title, "created": False, "reason": "duplicate"}

        summary = item.summary
        if not summary and canonical:
            summary = await self._fetch_summary(canonical)

        slug = await unique_slug(session, Story, item.title)
        story = Story(
            title=item.title,
            slug=slug,
            url=canonical,
            author=item.author,
            image_url=item.image_url,
            source_published_at=item.published_at,
            summary=summary,
            category=source.category,
            status="DISCOVERED",
            discovered_at=datetime.now(timezone.utc),
        )
        session.add(story)
        await session.flush()
        session.add(
            StorySource(
                story_id=story.id,
                source_id=source.id,
                relationship_note="primary",
                relevance_score=1.0,
            )
        )
        return {"title": item.title, "created": True, "reason": None}

    async def _fetch_summary(self, url: str) -> str | None:
        try:
            title, paragraphs = await self._text_extractor.extract(url)
            if paragraphs:
                combined = " ".join(paragraphs[:3])[:500]
                return combined if combined.strip() else None
        except (TextExtractionError, Exception) as exc:
            logger.debug("Failed to fetch summary from %s: %s", url, exc)
        return None

    async def _find_match(
        self, session: AsyncSession, source: Source, item: FeedItem, canonical: str
    ) -> Story | None:
        by_url = await session.scalar(
            select(Story).where(Story.url == canonical, Story.status != "MERGED")
        )
        if by_url is not None:
            return by_url
        window_start = datetime.now(timezone.utc) - timedelta(days=DUPLICATE_WINDOW_DAYS)
        same_source = (
            await session.execute(
                select(Story)
                .join(StorySource)
                .where(
                    StorySource.source_id == source.id,
                    Story.status != "MERGED",
                    Story.discovered_at >= window_start,
                )
            )
        ).scalars().all()
        expected = normalize_title(item.title)
        for candidate in same_source:
            if normalize_title(candidate.title) == expected:
                return candidate

        candidates = (
            await session.execute(
                select(Story)
                .where(
                    Story.status != "MERGED",
                    Story.discovered_at >= window_start,
                    Story.url.is_not(None),
                )
                .order_by(Story.discovered_at.desc())
                .limit(FUZZY_CANDIDATE_LIMIT)
            )
        ).scalars().all()

        own_ids = set(
            (
                await session.execute(
                    select(StorySource.story_id).where(StorySource.source_id == source.id)
                )
            ).scalars().all()
        )
        best: Story | None = None
        best_score = 0.0
        for candidate in candidates:
            if candidate.id in own_ids:
                continue
            if canonicalize_url(candidate.url) == canonical:
                continue
            if normalize_title(candidate.title) == expected:
                return candidate
            if candidate.url is None:
                continue
            if is_same_event(item.title, item.summary, candidate.title, candidate.summary):
                score = pair_score(
                    item.title, item.summary, candidate.title, candidate.summary
                )
                if score > best_score:
                    best = candidate
                    best_score = score
        return best

    async def _link_if_missing(
        self, session: AsyncSession, story: Story, source: Source
    ) -> None:
        linked = await session.scalar(
            select(StorySource).where(
                StorySource.story_id == story.id,
                StorySource.source_id == source.id,
            )
        )
        if linked is not None:
            return
        session.add(
            StorySource(
                story_id=story.id,
                source_id=source.id,
                relationship_note="secondary",
                relevance_score=0.9,
            )
        )

    async def _record_fetch_failure(self, source: Source, error: str) -> None:
        async with self._session_factory() as session:
            stored = await session.get(Source, source.id)
            if stored is not None:
                stored.last_fetched_at = datetime.now(timezone.utc)
                stored.last_fetch_error = error[:500]
                await session.commit()