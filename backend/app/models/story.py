from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

STORY_STATUSES = (
    "DISCOVERED",
    "RESEARCHING",
    "VERIFICATION",
    "DRAFT",
    "REVIEW",
    "APPROVED",
    "PUBLISHED",
    "REJECTED",
)


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    slug: Mapped[str] = mapped_column(String(600), unique=True, index=True)
    summary: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="DISCOVERED")
    importance_score: Mapped[float | None] = mapped_column(Float)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    sources: Mapped[list["StorySource"]] = relationship(
        back_populates="story", cascade="all, delete-orphan"
    )
    article: Mapped["Article | None"] = relationship(back_populates="story")


class StorySource(Base):
    __tablename__ = "story_sources"

    story_id: Mapped[int] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"), primary_key=True
    )
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True
    )
    relationship_note: Mapped[str | None] = mapped_column("relationship", String(100))
    relevance_score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    story: Mapped[Story] = relationship(back_populates="sources")
    source: Mapped["Source"] = relationship()