"""Job handler for backfilling missing story summaries."""

import logging

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.story import Story
from app.tools.text_extraction import TextExtractionError, TextExtractionTool
from app.workers.jobs import job_runner

logger = logging.getLogger(__name__)

BATCH_LIMIT = 20


async def _backfill_one(story: Story, extractor: TextExtractionTool) -> dict:
    if not story.url:
        return {"story_id": story.id, "status": "skipped", "reason": "no_url"}
    try:
        title, paragraphs = await extractor.extract(story.url)
        if paragraphs:
            summary = " ".join(paragraphs[:3])[:500]
            if summary.strip():
                story.summary = summary
                return {"story_id": story.id, "status": "updated", "title": story.title}
    except (TextExtractionError, Exception) as exc:
        logger.debug("Backfill failed for story %s: %s", story.id, exc)
    return {"story_id": story.id, "status": "skipped", "reason": "extraction_failed"}


async def handle_backfill_summaries(payload: dict) -> list[dict]:
    limit = int(payload.get("limit") or BATCH_LIMIT)
    extractor = TextExtractionTool()

    async with async_session_factory() as session:
        stories = (
            await session.execute(
                select(Story)
                .where(Story.summary.is_(None), Story.url.is_not(None), Story.status != "MERGED")
                .order_by(Story.discovered_at.asc())
                .limit(limit)
            )
        ).scalars().all()

        results = []
        for story in stories:
            result = await _backfill_one(story, extractor)
            results.append(result)

        await session.commit()
    return results


job_runner.register("backfill_summaries", handle_backfill_summaries)
