from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.models.claim import Claim
from app.models.story import Story
from app.schemas.ingestion import IngestionRunResponse
from app.schemas.verification import ClaimUpdate, StoryVerificationRead
from app.workers.jobs import job_runner

router = APIRouter(tags=["verification"])


@router.post("/run", response_model=IngestionRunResponse, status_code=202)
async def run_verification():
    job = job_runner.submit("verify_story")
    return IngestionRunResponse(job_id=job.job_id, job_name=job.name, status=job.status)


@router.post(
    "/stories/{story_id}", response_model=IngestionRunResponse, status_code=202
)
async def verify_story(
    story_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    story = await session.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    job = job_runner.submit("verify_story", {"story_id": story_id})
    return IngestionRunResponse(job_id=job.job_id, job_name=job.name, status=job.status)


@router.get("/stories/{story_id}", response_model=StoryVerificationRead)
async def get_story_verification(
    story_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    story = await session.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")

    claims = (
        await session.execute(
            select(Claim)
            .options(selectinload(Claim.evidences))
            .where(Claim.story_id == story_id)
            .order_by(Claim.created_at.asc())
        )
    ).scalars().all()

    verified_claims = [c for c in claims if c.status != "UNCONFIRMED"]
    confidences = [c.confidence_score for c in verified_claims if c.confidence_score is not None]
    overall = sum(confidences) / len(confidences) if confidences else 0.0

    return StoryVerificationRead(
        story_id=story.id,
        title=story.title,
        claims=[
            {
                "id": c.id,
                "claim_text": c.claim_text,
                "status": c.status,
                "confidence_score": c.confidence_score,
                "evidences": [
                    {
                        "id": e.id,
                        "evidence_text": e.evidence_text,
                        "url": e.url,
                        "source_id": e.source_id,
                    }
                    for e in c.evidences
                ],
            }
            for c in claims
        ],
        overall_confidence=overall,
        verification_summary=f"{len(verified_claims)}/{len(claims)} claims verified.",
    )


@router.patch("/claims/{claim_id}")
async def update_claim(
    claim_id: int,
    update: ClaimUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    claim = await session.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")

    if update.status is not None:
        claim.status = update.status
    if update.confidence_score is not None:
        claim.confidence_score = update.confidence_score

    await session.commit()
    return {"id": claim.id, "status": claim.status, "confidence_score": claim.confidence_score}
