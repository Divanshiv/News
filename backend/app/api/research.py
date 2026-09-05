from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.models.claim import Claim
from app.models.research import ResearchRun
from app.models.story import Story, StorySource
from app.schemas.ingestion import IngestionRunResponse
from app.schemas.research import (
    ClaimRead,
    ResearchRunRead,
    ResearchSourceRead,
    StoryResearchRead,
)
from app.workers.jobs import job_runner

router = APIRouter(tags=["research"])


@router.post("/run", response_model=IngestionRunResponse, status_code=202)
async def run_research():
    job = job_runner.submit("research_story")
    return IngestionRunResponse(job_id=job.job_id, job_name=job.name, status=job.status)


@router.post(
    "/stories/{story_id}", response_model=IngestionRunResponse, status_code=202
)
async def research_story(
    story_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    story = await session.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    job = job_runner.submit("research_story", {"story_id": story_id})
    return IngestionRunResponse(job_id=job.job_id, job_name=job.name, status=job.status)


@router.get("/runs/{story_id}", response_model=StoryResearchRead)
async def get_story_research(
    story_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    story = await session.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")

    runs = (
        await session.execute(
            select(ResearchRun)
            .where(ResearchRun.story_id == story_id)
            .order_by(ResearchRun.started_at.desc())
        )
    ).scalars().all()

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

    research_links = [
        ResearchSourceRead(
            source_id=link.source_id,
            name=link.source.name if link.source else None,
            url=link.source.url if link.source else None,
            relationship=link.relationship_note or "research",
            relevance_score=link.relevance_score,
        )
        for link in links
        if link.relationship_note and link.relationship_note.startswith("research")
    ]

    return StoryResearchRead(
        story_id=story.id,
        title=story.title,
        runs=[ResearchRunRead.model_validate(run) for run in runs],
        sources=research_links,
        claims=[
            ClaimRead(
                id=claim.id,
                claim_text=claim.claim_text,
                status=claim.status,
                confidence_score=claim.confidence_score,
                evidences=[
                    {
                        "id": evidence.id,
                        "evidence_text": evidence.evidence_text,
                        "url": evidence.url,
                        "source_id": evidence.source_id,
                    }
                    for evidence in claim.evidences
                ],
            )
            for claim in claims
        ],
    )