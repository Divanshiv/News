from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.story import Story
from app.schemas.ingestion import IngestionRunResponse
from app.workers.jobs import job_runner

router = APIRouter(tags=["scout"])


@router.post("/run", response_model=IngestionRunResponse, status_code=202)
async def run_scout():
    job = job_runner.submit("run_scout")
    return IngestionRunResponse(job_id=job.job_id, job_name=job.name, status=job.status)


@router.post(
    "/stories/{story_id}", response_model=IngestionRunResponse, status_code=202
)
async def scout_story(
    story_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    story = await session.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    job = job_runner.submit("run_scout", {"story_id": story_id})
    return IngestionRunResponse(job_id=job.job_id, job_name=job.name, status=job.status)