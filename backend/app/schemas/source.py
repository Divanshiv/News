from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.source import SOURCE_CATEGORIES, SOURCE_TYPES


class SourceBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=1, max_length=500)
    rss_url: str | None = Field(default=None, max_length=500)
    source_type: str = Field(default="news")
    category: str | None = Field(default=None)
    reliability_score: float = Field(default=0.0, ge=0.0, le=1.0)
    active: bool = True
    license_notes: str | None = None


class SourceCreate(SourceBase):
    pass


class SourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    url: str | None = Field(default=None, min_length=1, max_length=500)
    rss_url: str | None = Field(default=None, max_length=500)
    source_type: str | None = None
    category: str | None = None
    reliability_score: float | None = Field(default=None, ge=0.0, le=1.0)
    active: bool | None = None
    license_notes: str | None = None


class SourceRead(SourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime