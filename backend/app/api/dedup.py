from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.story import Story
from app.schemas.dedup import (
    DedupCandidateRead,
    DedupMergeRequest,
    DedupMergeResponse,
)
from app.schemas.ingestion import IngestionRunResponse
from app.services.dedup.merge import MergeError, merge_stories
from app.services.dedup.similarity import (
    REVIEW_MIN,
    TITLE_STRONG,
    is_same_event,
    pair_score,
)
from app.services.ingestion import DUPLICATE_WINDOW_DAYS, FUZZY_CANDIDATE_LIMIT
from app.workers.jobs import job_runner

router = APIRouter(tags=["dedup"])

SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("/run", response_model=IngestionRunResponse, status_code=202)
async def run_dedupe():
    job = job_runner.submit("dedupe_all")
    return IngestionRunResponse(job_id=job.job_id, job_name=job.name, status=job.status)


@router.post("/merge", response_model=DedupMergeResponse)
async def merge_stories_endpoint(
    body: DedupMergeRequest, session: SessionDep
) -> DedupMergeResponse:
    try:
        report = await merge_stories(session, body.keep_id, body.absorb_id)
    except MergeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return DedupMergeResponse(**report)


@router.get("/candidates", response_model=list[DedupCandidateRead])
async def dedup_candidates(
    session: SessionDep,
    min_score: float = Query(REVIEW_MIN, ge=0.0, le=1.0),
    limit: int = Query(50, ge=1, le=200),
) -> list[DedupCandidateRead]:
    window_start = datetime.now(timezone.utc) - timedelta(days=DUPLICATE_WINDOW_DAYS)
    stories = (
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

    pairs: list[tuple[float, Story, Story]] = []
    for i, story_a in enumerate(stories):
        for story_b in stories[i + 1 :]:
            if story_a.title and story_b.title and is_same_event(
                story_a.title, story_a.summary, story_b.title, story_b.summary
            ):
                continue
            score = pair_score(
                story_a.title, story_a.summary, story_b.title, story_b.summary
            )
            if score >= min_score and score < TITLE_STRONG:
                pairs.append((score, story_a, story_b))

    pairs.sort(key=lambda pair: pair[0], reverse=True)
    return [
        DedupCandidateRead(
            story_id_a=a.id,
            title_a=a.title,
            story_id_b=b.id,
            title_b=b.title,
            score=round(score, 3),
        )
        for score, a, b in pairs[:limit]
    ]