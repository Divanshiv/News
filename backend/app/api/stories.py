from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.models.source import Source
from app.models.story import Story, StorySource
from app.schemas.common import ListResponse
from app.schemas.story import StoryCreate, StoryRead, StoryUpdate
from app.services.slugs import unique_slug

router = APIRouter(tags=["stories"])

_STORY_LOAD = selectinload(Story.sources).selectinload(StorySource.source)


def _to_read(story: Story) -> StoryRead:
    read = StoryRead.model_validate(story)
    read.source_names = [
        link.source.name for link in story.sources if link.source is not None
    ]
    return read


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
        select(Story)
        .options(_STORY_LOAD)
        .where(*filters)
        .order_by(Story.discovered_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return ListResponse(
        items=[_to_read(s) for s in result.scalars().all()],
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
    await session.refresh(story, attribute_names=["sources"])
    return _to_read(story)


@router.get("/{story_id}", response_model=StoryRead)
async def get_story(
    story_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    story = await session.get(Story, story_id, options=[_STORY_LOAD])
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    return _to_read(story)


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
    refreshed = await session.execute(
        select(Story)
        .options(_STORY_LOAD)
        .where(Story.id == story_id)
        .execution_options(populate_existing=True)
    )
    return _to_read(refreshed.scalar_one())


@router.delete("/{story_id}", status_code=204)
async def delete_story(
    story_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    story = await session.get(Story, story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    # Bulk delete: let the database cascade dependents (claims, evidence,
    # research runs, articles, links, social/media, publishing jobs) and
    # SET NULL agent runs / merged references. The ORM would otherwise try
    # to nullify non-null FKs (e.g. articles.story_id) and fail.
    await session.execute(delete(Story).where(Story.id == story_id))
    await session.commit()