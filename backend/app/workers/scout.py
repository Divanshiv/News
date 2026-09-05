from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.agents.scout import ScoutAgent
from app.core.database import async_session_factory
from app.models.story import Story
from app.services.llm import get_provider
from app.services.llm.base import LLMProvider
from app.workers.jobs import job_runner

logger = logging.getLogger(__name__)

BATCH_LIMIT = 50


async def handle_run_scout(
    payload: dict, *, provider: LLMProvider | None = None
) -> list[dict]:
    agent = ScoutAgent(provider or get_provider())
    story_id = payload.get("story_id")
    limit = int(payload.get("limit") or BATCH_LIMIT)
    now = datetime.now(timezone.utc)
    report: list[dict] = []
    async with async_session_factory() as session:
        if story_id is not None:
            story = await session.get(Story, story_id)
            stories = [story] if story is not None else []
        else:
            stories = (
                await session.execute(
                    select(Story)
                    .where(
                        Story.status == "DISCOVERED",
                        Story.should_research.is_(None),
                    )
                    .order_by(Story.discovered_at.asc())
                    .limit(limit)
                )
            ).scalars().all()
        for story in stories:
            if story.status == "MERGED":
                report.append(
                    {
                        "story_id": story.id,
                        "title": story.title,
                        "error": "story is merged",
                    }
                )
                continue
            try:
                verdict = await agent.scout(
                    title=story.title,
                    summary=story.summary,
                    category_hint=story.category,
                    published_at=story.source_published_at,
                )
            except Exception:
                logger.warning("scout failed for story %s", story.id, exc_info=True)
                report.append(
                    {
                        "story_id": story.id,
                        "title": story.title,
                        "error": "scout failure",
                    }
                )
                continue
            story.should_research = verdict.should_research
            story.importance_score = float(verdict.importance)
            story.category = verdict.category or story.category
            story.scout_reason = verdict.reason
            story.scouted_at = now
            report.append(
                {
                    "story_id": story.id,
                    "title": story.title,
                    "should_research": verdict.should_research,
                    "importance": verdict.importance,
                    "category": verdict.category,
                    "reason": verdict.reason,
                }
            )
        await session.commit()
    return report


job_runner.register("run_scout", handle_run_scout)