from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.source import Source
from app.models.story import Story, StorySource
from app.schemas.common import ListResponse
from app.schemas.story import StoryCreate, StoryRead, StoryUpdate
from app.services.slugs import unique_slug

router = APIRouter(tags=["stories"])


@router.get("", response_model=ListResponse[StoryRead])
async def list_stories(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: str | None = None,
    category: str | None = None,
):
    filters = []
    if status:
        filters.append(Story.status == status)
    if category:
        filters.append(Story.category == category)

    total = await session.scalar(select(func.count()).select_from(Story).where(*filters))
    result = await session.execute(
        select(Story).where(*filters).order_by(Story.discovered_at.desc()).limit(limit).offset(offset)
    )
    return ListResponse(
        items=[StoryRead.model_validate(s) for s in result.scalars().all()],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=StoryRead, status_code=201)
async def create_story(
    payload: StoryCreate,
    session: AsyncSession = Depends(get_db_session),
):
    data = payload.model_dump(exclude={"source_id"})
    data["slug"] = await unique_slug(session, Story, payload.title)
    story = Story(**data)
    session.add(story)
    await session.flush()

    if payload.source_id:
        source = await session.get(Source, payload.source_id)
        if source is None:
            raise HTTPException(status_code=404, detail="Source not found")
        session.add(
            StorySource(story_id=story.id, source_id=payload.source_id, relationship_note="primary")
        )

    await session.commit()
    await session.refresh(story)
    return story


@router.get("/{story_id}", response_model=StoryRead)
async def get_story(
    story_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    story = await session.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.patch("/{story_id}", response_model=StoryRead)
async def update_story(
    story_id: int,
    payload: StoryUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    story = await session.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    updates = payload.model_dump(exclude_unset=True)
    if "title" in updates and updates["title"] != story.title:
        updates["slug"] = await unique_slug(session, Story, updates["title"])
    for field, value in updates.items():
        setattr(story, field, value)
    await session.commit()
    await session.refresh(story)
    return story


@router.delete("/{story_id}", status_code=204)
async def delete_story(
    story_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    story = await session.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    await session.delete(story)
    await session.commit()