"""Public, non-secret service metadata for the operator dashboard."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.meta import ServiceConfigRead

router = APIRouter(tags=["meta"])


@router.get("/config", response_model=ServiceConfigRead)
async def service_config() -> ServiceConfigRead:
    settings = get_settings()
    return ServiceConfigRead(
        app_name=settings.app_name,
        app_version=settings.app_version,
        environment=settings.environment,
        llm_provider=settings.llm_provider,
        ollama_url=settings.ollama_url,
        ollama_model=settings.ollama_model,
    )
