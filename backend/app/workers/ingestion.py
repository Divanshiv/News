"""Job handlers for the ingestion pipeline.

Handlers are registered on the shared job_runner at import time so the
runner works in any server (uvicorn lifespan, test transports, etc.).
"""

import logging

from app.services.ingestion import IngestionService
from app.workers.jobs import job_runner

logger = logging.getLogger(__name__)


async def handle_ingest_all(payload: dict) -> list[dict]:
    service = IngestionService()
    results = await service.ingest_all()
    logger.info("ingest_all complete", extra={"status": "ok", "source_count": len(results)})
    return [result.to_dict() for result in results]


async def handle_ingest_source(payload: dict) -> dict:
    source_id = payload["source_id"]
    service = IngestionService()
    source = await service.get_source(source_id)
    if source is None:
        raise ValueError(f"source {source_id} not found")
    result = await service.ingest_source(source)
    logger.info(
        "ingest_source complete",
        extra={"source_id": source_id, "status": result.status, "created": result.created},
    )
    return result.to_dict()


job_runner.register("ingest_all", handle_ingest_all)
job_runner.register("ingest_source", handle_ingest_source)