from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

ARTICLE_STATUSES = ("DRAFT", "REVIEW", "APPROVED", "PUBLISHED")


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    story_id: Mapped[int] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"), unique=True, index=True
    )
    headline: Mapped[str] = mapped_column(String(500))
    subheadline: Mapped[str | None] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(Text)
    seo_title: Mapped[str | None] = mapped_column(String(500))
    seo_description: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    story: Mapped["Story"] = relationship(back_populates="article")