"""Job handlers for the verification pipeline."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agents.verification import VerificationAgent
from app.core.database import async_session_factory
from app.models.claim import Claim, Evidence
from app.models.story import Story
from app.services.llm import get_provider
from app.services.llm.base import LLMProvider
from app.workers.jobs import job_runner

logger = logging.getLogger(__name__)

BATCH_LIMIT = 20


async def _gather_claims_for_verification(session, story_id: int) -> list[dict]:
    claims = (
        await session.execute(
            select(Claim)
            .options(selectinload(Claim.evidences))
            .where(Claim.story_id == story_id)
            .order_by(Claim.created_at.asc())
        )
    ).scalars().all()

    result = []
    for claim in claims:
        evidence_urls = [e.url for e in claim.evidences if e.url]
        evidence_texts = [e.evidence_text for e in claim.evidences]
        result.append({
            "claim_id": claim.id,
            "claim_text": claim.claim_text,
            "evidence_urls": evidence_urls,
            "evidence_texts": evidence_texts,
        })
    return result


async def _verify_one(
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

        claims_data = await _gather_claims_for_verification(session, story_id)
        if not claims_data:
            return {**report, "error": "no claims to verify", "title": story.title}

        agent = VerificationAgent(provider or get_provider())
        result = await agent.verify(story_id=story_id, claims=claims_data)

        for verified_claim in result.claims:
            claim = await session.get(Claim, verified_claim.claim_id)
            if claim:
                claim.status = verified_claim.status
                claim.confidence_score = verified_claim.confidence

        verified_count = sum(1 for c in result.claims if c.status != "UNCONFIRMED")
        if verified_count > 0:
            story.status = "VERIFICATION"
            story.confidence_score = result.overall_confidence

        await session.commit()
        report.update({
            "title": story.title,
            "claims_verified": len(result.claims),
            "overall_confidence": result.overall_confidence,
            "summary": result.summary,
        })
    return report


async def handle_verify_story(
    payload: dict,
    *,
    provider: LLMProvider | None = None,
) -> list[dict]:
    story_id = payload.get("story_id")
    limit = int(payload.get("limit") or BATCH_LIMIT)
    if story_id is not None:
        return [await _verify_one(story_id=story_id, provider=provider)]

    async with async_session_factory() as session:
        stories = (
            await session.execute(
                select(Story)
                .where(
                    Story.status == "RESEARCHING",
                )
                .order_by(Story.researched_at.asc())
                .limit(limit)
            )
        ).scalars().all()
        ids = [story.id for story in stories]
    return [
        await _verify_one(story_id=sid, provider=provider) for sid in ids
    ]


job_runner.register("verify_story", handle_verify_story)
