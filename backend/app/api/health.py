from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(session: AsyncSession = Depends(get_db_session)):
    settings = get_settings()
    database = "connected"
    status = "ok"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        database = "unavailable"
        status = "degraded"
    return {
        "status": status,
        "service": "ai-newsroom-backend",
        "version": settings.app_version,
        "environment": settings.environment,
        "database": database,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }