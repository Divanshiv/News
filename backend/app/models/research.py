from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

RESEARCH_RUN_STATUSES = ("PENDING", "RUNNING", "COMPLETED", "FAILED")


class ResearchRun(Base):
    __tablename__ = "research_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    story_id: Mapped[int] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"), index=True
    )
    agent_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    input: Mapped[dict | None] = mapped_column(JSON)
    output: Mapped[dict | None] = mapped_column(JSON)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)