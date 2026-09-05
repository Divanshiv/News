"""Job handlers for story deduplication and merging."""

import logging

from app.core.database import async_session_factory
from app.services.dedup.merge import dedupe_all
from app.workers.jobs import job_runner

logger = logging.getLogger(__name__)


async def handle_dedupe_all(payload: dict) -> list[dict]:
    async with async_session_factory() as session:
        reports = await dedupe_all(session)
    logger.info(
        "dedupe_all complete",
        extra={"status": "ok", "merged_groups": len(reports)},
    )
    return reports


job_runner.register("dedupe_all", handle_dedupe_all)