from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

SOURCE_TYPES = ("official", "news", "research", "government", "social", "blog", "other")

SOURCE_CATEGORIES = ("AI", "Technology", "Business", "India", "Science", "Cybersecurity", "Space", "World")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(500))
    rss_url: Mapped[str | None] = mapped_column(String(500))
    source_type: Mapped[str] = mapped_column(String(20), default="news")
    category: Mapped[str | None] = mapped_column(String(50))
    reliability_score: Mapped[float] = mapped_column(Float, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    license_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )