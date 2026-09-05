from fastapi import APIRouter

from app.schemas.ingestion import IngestionRunResponse
from app.workers.jobs import job_runner

router = APIRouter(tags=["backfill"])


@router.post("/summaries", response_model=IngestionRunResponse, status_code=202)
async def run_backfill_summaries():
    job = job_runner.submit("backfill_summaries")
    return IngestionRunResponse(job_id=job.job_id, job_name=job.name, status=job.status)
