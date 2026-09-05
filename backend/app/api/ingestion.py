from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.source import Source
from app.schemas.ingestion import IngestionJobRead, IngestionRunResponse
from app.workers.jobs import job_runner

router = APIRouter(tags=["ingestion"])


def _job_to_read(job) -> IngestionJobRead:
    def epoch(dt: float | None) -> datetime | None:
        return datetime.fromtimestamp(dt, tz=timezone.utc) if dt is not None else None

    result = job.result
    if isinstance(result, dict):
        result = [result]

    return IngestionJobRead(
        job_id=job.job_id,
        job_name=job.name,
        status=job.status,
        created_at=epoch(job.created_at),
        started_at=epoch(job.started_at),
        completed_at=epoch(job.completed_at),
        error=job.error,
        result=result,
    )


@router.post("/run", response_model=IngestionRunResponse, status_code=202)
async def run_ingestion():
    job = job_runner.submit("ingest_all")
    return IngestionRunResponse(job_id=job.job_id, job_name=job.name, status=job.status)


@router.post(
    "/sources/{source_id}/fetch", response_model=IngestionRunResponse, status_code=202
)
async def fetch_source(
    source_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    source = await session.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    if not source.rss_url:
        raise HTTPException(status_code=400, detail="Source has no RSS URL configured")
    job = job_runner.submit("ingest_source", {"source_id": source_id})
    return IngestionRunResponse(job_id=job.job_id, job_name=job.name, status=job.status)


@router.get("/jobs/{job_id}", response_model=IngestionJobRead)
async def get_job(job_id: str):
    job = job_runner.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_read(job)