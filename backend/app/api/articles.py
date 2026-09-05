from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.article import Article
from app.models.story import Story
from app.schemas.article import ArticleCreate, ArticleRead, ArticleUpdate
from app.schemas.common import ListResponse

router = APIRouter(tags=["articles"])


@router.get("", response_model=ListResponse[ArticleRead])
async def list_articles(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: str | None = None,
    story_id: int | None = None,
):
    filters = []
    if status:
        filters.append(Article.status == status)
    if story_id is not None:
        filters.append(Article.story_id == story_id)

    total = await session.scalar(select(func.count()).select_from(Article).where(*filters))
    result = await session.execute(
        select(Article).where(*filters).order_by(Article.updated_at.desc()).limit(limit).offset(offset)
    )
    return ListResponse(
        items=[ArticleRead.model_validate(a) for a in result.scalars().all()],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=ArticleRead, status_code=201)
async def create_article(
    payload: ArticleCreate,
    session: AsyncSession = Depends(get_db_session),
):
    story = await session.get(Story, payload.story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    article = Article(**payload.model_dump())
    if article.status == "PUBLISHED":
        article.published_at = datetime.now(timezone.utc)
    session.add(article)
    await session.commit()
    await session.refresh(article)
    return article


@router.get("/{article_id}", response_model=ArticleRead)
async def get_article(
    article_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    article = await session.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.patch("/{article_id}", response_model=ArticleRead)
async def update_article(
    article_id: int,
    payload: ArticleUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    article = await session.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    updates = payload.model_dump(exclude_unset=True)
    if updates.get("status") == "PUBLISHED" and article.published_at is None:
        article.published_at = datetime.now(timezone.utc)
    for field, value in updates.items():
        setattr(article, field, value)
    await session.commit()
    await session.refresh(article)
    return article


@router.delete("/{article_id}", status_code=204)
async def delete_article(
    article_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    article = await session.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    await session.delete(article)
    await session.commit()