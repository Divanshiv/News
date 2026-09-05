"""Job handlers for the article writing pipeline."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agents.writer import WriterAgent
from app.core.database import async_session_factory
from app.models.article import Article
from app.models.claim import Claim, Evidence
from app.models.story import Story, StorySource
from app.services.llm import get_provider
from app.services.llm.base import LLMProvider
from app.workers.jobs import job_runner

logger = logging.getLogger(__name__)

BATCH_LIMIT = 10


async def _gather_writing_package(session, story_id: int) -> dict:
    claims = (
        await session.execute(
            select(Claim)
            .options(selectinload(Claim.evidences))
            .where(Claim.story_id == story_id)
            .order_by(Claim.created_at.asc())
        )
    ).scalars().all()

    links = (
        await session.execute(
            select(StorySource)
            .options(selectinload(StorySource.source))
            .where(StorySource.story_id == story_id)
        )
    ).scalars().all()

    claim_payload = [
        {
            "claim_id": claim.id,
            "claim_text": claim.claim_text,
            "status": claim.status,
            "confidence": claim.confidence_score,
            "evidence_urls": [e.url for e in claim.evidences if e.url],
        }
        for claim in claims
    ]

    source_urls = []
    for link in links:
        if link.source and link.source.url:
            source_urls.append(link.source.url)
    for claim in claims:
        for evidence in claim.evidences:
            if evidence.url and evidence.url not in source_urls:
                source_urls.append(evidence.url)

    return {
        "claims": claim_payload,
        "source_urls": source_urls,
    }


async def _write_one(
    *,
    story_id: int,
    provider: LLMProvider | None = None,
) -> dict:
    report: dict = {"story_id": story_id}
    async with async_session_factory() as session:
        story = await session.get(Story, story_id)
        if story is None:
            return {**report, "error": "story not found"}
        if story.status == "MERGED":
            return {**report, "error": "story is merged"}

        package = await _gather_writing_package(session, story_id)
        if not package["claims"]:
            return {**report, "error": "no claims to write from", "title": story.title}

        existing = (
            await session.execute(
                select(Article).where(Article.story_id == story_id).limit(1)
            )
        ).scalar_one_or_none()
        if existing is not None:
            return {**report, "error": "article already exists", "title": story.title}

        agent = WriterAgent(provider or get_provider())
        draft = await agent.write(
            title=story.title,
            summary=story.summary,
            category=story.category,
            claims=package["claims"],
            source_urls=package["source_urls"],
        )

        article = Article(
            story_id=story_id,
            headline=draft.headline,
            subheadline=draft.subheadline or None,
            summary=draft.summary,
            body=draft.body,
            seo_title=draft.seo_title,
            seo_description=draft.seo_description,
            status="DRAFT",
        )
        session.add(article)
        story.status = "DRAFT"
        await session.commit()
        report.update(
            {
                "title": story.title,
                "article_id": article.id,
                "headline": draft.headline,
            }
        )
    return report


async def handle_generate_article(
    payload: dict,
    *,
    provider: LLMProvider | None = None,
) -> list[dict]:
    story_id = payload.get("story_id")
    limit = int(payload.get("limit") or BATCH_LIMIT)
    if story_id is not None:
        return [await _write_one(story_id=story_id, provider=provider)]

    async with async_session_factory() as session:
        stories = (
            await session.execute(
                select(Story)
                .where(Story.status == "VERIFICATION")
                .order_by(Story.updated_at.asc())
                .limit(limit)
            )
        ).scalars().all()
        ids = [story.id for story in stories]
    return [
        await _write_one(story_id=sid, provider=provider) for sid in ids
    ]


job_runner.register("generate_article", handle_generate_article)