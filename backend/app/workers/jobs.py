"""In-process async background job runner.

Single-process deployments only; jobs are tracked in memory. For
multi-worker deployments, swap this for a real queue (Redis + ARQ)
while keeping the submit/get interface stable.
"""

import asyncio
import logging
import secrets
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

JobHandler = Callable[[dict[str, Any]], Awaitable[Any]]


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class Job:
    job_id: str
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    status: JobStatus = JobStatus.QUEUED
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    result: Any = None
    error: str | None = None


class JobRunner:
    def __init__(self, *, workers: int = 2) -> None:
        self._workers = workers
        self._handlers: dict[str, JobHandler] = {}
        self._jobs: dict[str, Job] = {}
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._tasks: list[asyncio.Task] = []
        self._started = False

    def register(self, name: str, handler: JobHandler) -> None:
        self._handlers[name] = handler

    def submit(self, name: str, payload: dict[str, Any] | None = None) -> Job:
        if name not in self._handlers:
            raise KeyError(f"no handler registered for job '{name}'")
        job = Job(job_id=secrets.token_hex(8), name=name, payload=payload or {})
        self._jobs[job.job_id] = job
        self._queue.put_nowait(job)
        self._ensure_workers()
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def recent(self, limit: int) -> list[Job]:
        jobs = sorted(self._jobs.values(), key=lambda job: job.created_at, reverse=True)
        return jobs[:limit]

    def start(self) -> None:
        self._ensure_workers()

    def shutdown(self) -> None:
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()
        self._started = False

    def reset(self) -> None:
        self.shutdown()
        self._jobs.clear()
        while not self._queue.empty():
            self._queue.get_nowait()
            self._queue.task_done()

    def _ensure_workers(self) -> None:
        if self._started:
            return
        loop = asyncio.get_running_loop()
        self._tasks = [loop.create_task(self._run_worker()) for _ in range(self._workers)]
        self._started = True

    async def _run_worker(self) -> None:
        while True:
            job = await self._queue.get()
            job.status = JobStatus.RUNNING
            job.started_at = time.time()
            try:
                job.result = await self._handlers[job.name](job.payload)
                job.status = JobStatus.COMPLETED
            except asyncio.CancelledError:
                job.status = JobStatus.FAILED
                job.error = "job cancelled"
                raise
            except Exception as exc:
                logger.exception("job %s (%s) failed", job.job_id, job.name)
                job.status = JobStatus.FAILED
                job.error = str(exc)
            finally:
                job.completed_at = time.time()
                self._queue.task_done()

job_runner = JobRunner()
