from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StoryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    url: str | None = Field(default=None, max_length=500)
    author: str | None = Field(default=None, max_length=200)
    image_url: str | None = Field(default=None, max_length=500)
    source_published_at: datetime | None = None
    summary: str | None = None
    category: str | None = Field(default=None, max_length=50)
    status: str = Field(default="DISCOVERED", max_length=20)
    importance_score: float | None = Field(default=None, ge=0.0, le=10.0)
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    source_id: int | None = None


class StoryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    url: str | None = Field(default=None, max_length=500)
    author: str | None = Field(default=None, max_length=200)
    image_url: str | None = Field(default=None, max_length=500)
    source_published_at: datetime | None = None
    summary: str | None = None
    category: str | None = Field(default=None, max_length=50)
    status: str | None = Field(default=None, max_length=20)
    importance_score: float | None = Field(default=None, ge=0.0, le=10.0)
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)


class StoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    url: str | None
    author: str | None
    image_url: str | None
    source_published_at: datetime | None
    summary: str | None
    category: str | None
    status: str
    importance_score: float | None
    confidence_score: float | None
    should_research: bool | None
    scout_reason: str | None
    discovered_at: datetime
    updated_at: datetime
    source_names: list[str] = []