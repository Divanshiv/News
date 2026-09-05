"""Job handlers for the research pipeline."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.agents.research import ResearchAgent
from app.core.config import get_settings
from app.core.database import async_session_factory
from app.models.research import ResearchRun
from app.models.story import Story
from app.services.llm import get_provider
from app.services.llm.base import LLMProvider
from app.services.research import persist_package
from app.tools import build_research_tools, ResearchTools
from app.workers.jobs import job_runner

logger = logging.getLogger(__name__)

BATCH_LIMIT = 20


def _build_agent(provider: LLMProvider, tools: ResearchTools) -> ResearchAgent:
    settings = get_settings()
    return ResearchAgent(
        provider,
        tools.search,
        tools.fetch,
        max_queries=settings.research_max_queries,
        fetch_limit=settings.research_fetch_limit,
        max_sources=settings.research_max_sources,
    )


async def _research_one(
    *,
    story_id: int,
    provider: LLMProvider | None = None,
    tools: ResearchTools | None = None,
) -> dict:
    report: dict = {"story_id": story_id}
    async with async_session_factory() as session:
        story = await session.get(Story, story_id)
        if story is None:
            return {**report, "error": "story not found"}
        if story.status == "MERGED":
            return {**report, "error": "story is merged"}
        existing = await session.execute(
            select(ResearchRun)
            .where(
                ResearchRun.story_id == story_id,
                ResearchRun.agent_name == "research",
                ResearchRun.status == "COMPLETED",
            )
            .limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            return {**report, "error": "already researched", "title": story.title}

        stale = await session.execute(
            select(ResearchRun).where(
                ResearchRun.story_id == story_id,
                ResearchRun.agent_name == "research",
                ResearchRun.status == "RUNNING",
            )
        )
        for run in stale.scalars().all():
            run.status = "FAILED"
            run.error = "superseded: worker restarted or re-run"
            run.completed_at = datetime.now(timezone.utc)

        research_run = ResearchRun(
            story_id=story_id,
            agent_name="research",
            status="RUNNING",
            input={"title": story.title, "summary": story.summary},
            started_at=datetime.now(timezone.utc),
        )
        session.add(research_run)
        await session.commit()

        try:
            effective_tools = tools or build_research_tools()
            agent = _build_agent(provider or get_provider(), effective_tools)
            package = await agent.research(
                title=story.title,
                summary=story.summary,
                category=story.category,
            )
        except Exception as exc:
            logger.warning("research failed for story %s", story_id, exc_info=True)
            research_run.status = "FAILED"
            research_run.error = str(exc)[:2000]
            research_run.completed_at = datetime.now(timezone.utc)
            await session.commit()
            return {**report, "error": "research failure", "title": story.title}

        created_run = await persist_package(session, story, package, research_run)
        await session.commit()
        report.update(
            {
                "title": story.title,
                "sources": len(package.sources),
                "claims": len(package.claims),
                "run_id": created_run.id,
            }
        )
    return report


async def handle_research_story(
    payload: dict,
    *,
    provider: LLMProvider | None = None,
    tools: ResearchTools | None = None,
) -> list[dict]:
    story_id = payload.get("story_id")
    limit = int(payload.get("limit") or BATCH_LIMIT)
    if story_id is not None:
        return [await _research_one(story_id=story_id, provider=provider, tools=tools)]

    async with async_session_factory() as session:
        stories = (
            await session.execute(
                select(Story)
                .where(
                    Story.status == "DISCOVERED",
                    Story.should_research.is_(True),
                )
                .order_by(Story.discovered_at.asc())
                .limit(limit)
            )
        ).scalars().all()
        ids = [story.id for story in stories]
    return [
        await _research_one(story_id=id, provider=provider, tools=tools) for id in ids
    ]


job_runner.register("research_story", handle_research_story)