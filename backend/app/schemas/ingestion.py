from datetime import datetime

from pydantic import BaseModel

from app.workers.jobs import JobStatus


class IngestionRunResponse(BaseModel):
    job_id: str
    job_name: str
    status: JobStatus


class SourceIngestResultRead(BaseModel):
    source_id: int
    source_name: str
    status: str
    fetched: int
    created: int
    skipped: int
    error: str | None = None


class IngestionJobRead(BaseModel):
    job_id: str
    job_name: str
    status: JobStatus
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    result: list[dict] | None = None


class JobSummaryRead(BaseModel):
    job_id: str
    job_name: str
    status: JobStatus
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None