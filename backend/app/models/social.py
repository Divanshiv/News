from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

SOCIAL_PLATFORMS = ("instagram",)
SOCIAL_POST_TYPES = ("image", "carousel", "reel")


class SocialPost(Base):
    __tablename__ = "social_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    story_id: Mapped[int] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[str] = mapped_column(String(20), default="instagram")
    post_type: Mapped[str] = mapped_column(String(20), default="carousel")
    caption: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    platform_post_id: Mapped[str | None] = mapped_column(String(200))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    story_id: Mapped[int] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(50))
    url: Mapped[str | None] = mapped_column(String(500))
    storage_path: Mapped[str | None] = mapped_column(String(500))
    license: Mapped[str | None] = mapped_column(String(100))
    attribution: Mapped[str | None] = mapped_column(String(500))
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON)