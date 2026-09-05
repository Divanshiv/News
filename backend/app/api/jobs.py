"""Recent background-job history for the operator dashboard."""

from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app.schemas.ingestion import JobSummaryRead
from app.workers.jobs import job_runner

router = APIRouter(tags=["jobs"])


def _dt(ts: float | None) -> datetime | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


@router.get("", response_model=list[JobSummaryRead])
async def list_jobs(
    limit: int = Query(default=25, ge=1, le=200),
) -> list[JobSummaryRead]:
    return [
        JobSummaryRead(
            job_id=job.job_id,
            job_name=job.name,
            status=job.status,
            created_at=_dt(job.created_at),
            started_at=_dt(job.started_at),
            completed_at=_dt(job.completed_at),
            error=job.error,
        )
        for job in job_runner.recent(limit)
    ]
