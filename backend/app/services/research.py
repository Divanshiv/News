"""Persistence for research runs: sources, story links, claims, evidence."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.research import ResearchPackage
from app.models.claim import Claim, Evidence
from app.models.research import ResearchRun
from app.models.story import Story, StorySource
from app.tools.source_lookup import SourceLookupTool, tier_for_url

RESEARCH_AGENT_NAME = "research"


async def persist_package(
    session: AsyncSession,
    story: Story,
    package: ResearchPackage,
    research_run: ResearchRun,
) -> ResearchRun:
    lookup = SourceLookupTool(session)
    link_counts: dict[str, int] = {}
    for source_item in package.sources:
        source = await lookup.get_or_create(
            url=source_item.url,
            name=source_item.title,
            category=story.category,
            source_type="news",
        )
        if source is None:
            continue
        tier = tier_for_url(source_item.url)
        if tier == "primary":
            source.reliability_score = max(source.reliability_score, 0.8)
        link = await session.execute(
            select(StorySource).where(
                StorySource.story_id == story.id,
                StorySource.source_id == source.id,
            )
        )
        if link.scalar_one_or_none() is None:
            session.add(
                StorySource(
                    story_id=story.id,
                    source_id=source.id,
                    relationship_note=f"research ({tier})",
                    relevance_score=source_item.relevance,
                )
            )
        link_counts[source_item.url] = source.id

    for claim_item in package.claims:
        claim = Claim(story_id=story.id, claim_text=claim_item.text)
        session.add(claim)
        await session.flush()
        for url in claim_item.source_urls:
            source_id = link_counts.get(url)
            session.add(
                Evidence(
                    claim_id=claim.id,
                    source_id=source_id,
                    evidence_text=claim_item.text,
                    url=url[:500],
                )
            )

    research_run.status = "COMPLETED"
    research_run.output = package.to_dict()
    research_run.completed_at = datetime.now(timezone.utc)
    story.status = "RESEARCHING"
    story.researched_at = datetime.now(timezone.utc)
    return research_run