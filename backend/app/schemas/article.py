from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ArticleCreate(BaseModel):
    story_id: int
    headline: str = Field(min_length=1, max_length=500)
    subheadline: str | None = Field(default=None, max_length=500)
    summary: str | None = None
    body: str | None = None
    seo_title: str | None = Field(default=None, max_length=500)
    seo_description: str | None = Field(default=None, max_length=1000)
    status: str = Field(default="DRAFT", max_length=20)


class ArticleUpdate(BaseModel):
    headline: str | None = Field(default=None, min_length=1, max_length=500)
    subheadline: str | None = Field(default=None, max_length=500)
    summary: str | None = None
    body: str | None = None
    seo_title: str | None = Field(default=None, max_length=500)
    seo_description: str | None = Field(default=None, max_length=1000)
    status: str | None = Field(default=None, max_length=20)
    published_at: datetime | None = None


class ArticleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    story_id: int
    headline: str
    subheadline: str | None
    summary: str | None
    body: str | None
    seo_title: str | None
    seo_description: str | None
    status: str
    published_at: datetime | None
    updated_at: datetime


class ArticleWithStory(ArticleRead):
    story_title: str | None = None
    story_category: str | None = None
    story_slug: str | None = None
    story_confidence: float | None = None
    story_url: str | None = None


class ArticleGenerateRequest(BaseModel):
    pass


class ArticleGenerateResponse(BaseModel):
    job_id: str
    job_name: str
    status: str