from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

CLAIM_STATUSES = ("CONFIRMED", "LIKELY", "UNCONFIRMED", "CONTRADICTED")


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(primary_key=True)
    story_id: Mapped[int] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"), index=True
    )
    claim_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="UNCONFIRMED")
    confidence_score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    evidences: Mapped[list["Evidence"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"))
    evidence_text: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(500))
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    claim: Mapped[Claim] = relationship(back_populates="evidences")