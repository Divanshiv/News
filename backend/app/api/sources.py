from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.source import Source
from app.schemas.common import ListResponse
from app.schemas.source import SourceCreate, SourceRead, SourceUpdate

router = APIRouter(tags=["sources"])


@router.get("", response_model=ListResponse[SourceRead])
async def list_sources(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    category: str | None = None,
    source_type: str | None = None,
    active: bool | None = None,
):
    filters = []
    if category:
        filters.append(Source.category == category)
    if source_type:
        filters.append(Source.source_type == source_type)
    if active is not None:
        filters.append(Source.active == active)

    total = await session.scalar(select(func.count()).select_from(Source).where(*filters))
    result = await session.execute(
        select(Source).where(*filters).order_by(Source.name).limit(limit).offset(offset)
    )
    return ListResponse(
        items=[SourceRead.model_validate(s) for s in result.scalars().all()],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=SourceRead, status_code=201)
async def create_source(
    payload: SourceCreate,
    session: AsyncSession = Depends(get_db_session),
):
    source = Source(**payload.model_dump())
    session.add(source)
    await session.commit()
    await session.refresh(source)
    return source


@router.get("/{source_id}", response_model=SourceRead)
async def get_source(
    source_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    source = await session.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.patch("/{source_id}", response_model=SourceRead)
async def update_source(
    source_id: int,
    payload: SourceUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    source = await session.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, field, value)
    await session.commit()
    await session.refresh(source)
    return source


@router.delete("/{source_id}", status_code=204)
async def delete_source(
    source_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    source = await session.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    await session.delete(source)
    await session.commit()