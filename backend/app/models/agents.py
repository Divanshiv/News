from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

AGENT_RUN_STATUSES = ("PENDING", "RUNNING", "COMPLETED", "FAILED")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_name: Mapped[str] = mapped_column(String(100))
    story_id: Mapped[int | None] = mapped_column(
        ForeignKey("stories.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    model: Mapped[str | None] = mapped_column(String(100))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    duration: Mapped[float | None] = mapped_column()
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PublishingJob(Base):
    __tablename__ = "publishing_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    story_id: Mapped[int] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[str] = mapped_column(String(20), default="instagram")
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)