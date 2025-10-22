"""API endpoints for data source management."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from voc_app.models import DataSource

from .dependencies import DatabaseSession, Pagination

router = APIRouter()


class DataSourceCreate(BaseModel):
    """Schema for creating a data source."""

    name: str = Field(..., min_length=1, max_length=255)
    platform: str = Field(..., min_length=1, max_length=50)
    config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    schedule: str | None = None


class DataSourceUpdate(BaseModel):
    """Schema for updating a data source."""

    name: str | None = None
    config: dict[str, Any] | None = None
    is_active: bool | None = None
    schedule: str | None = None


class DataSourceResponse(BaseModel):
    """Schema for data source response."""

    id: str
    name: str
    platform: str
    config: dict[str, Any]
    is_active: bool
    schedule: str | None
    last_crawl_at: str | None
    created_at: str
    updated_at: str | None

    class Config:
        from_attributes = True


@router.get("", response_model=list[DataSourceResponse])
async def list_sources(
    session: DatabaseSession,
    pagination: Pagination,
    platform: str | None = None,
    is_active: bool | None = None,
):
    """List all data sources with optional filtering."""
    query = select(DataSource)

    if platform:
        query = query.where(DataSource.platform == platform)
    
    if is_active is not None:
        query = query.where(DataSource.is_active == is_active)

    query = query.offset(pagination.skip).limit(pagination.limit)
    
    result = await session.execute(query)
    sources = result.scalars().all()

    return [
        DataSourceResponse(
            id=str(source.id),
            name=source.name,
            platform=source.platform,
            config=source.config or {},
            is_active=source.is_active,
            schedule=source.schedule,
            last_crawl_at=source.last_crawl_at.isoformat() if source.last_crawl_at else None,
            created_at=source.created_at.isoformat(),
            updated_at=source.updated_at.isoformat() if source.updated_at else None,
        )
        for source in sources
    ]


@router.post("", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(session: DatabaseSession, data: DataSourceCreate):
    """Create a new data source."""
    source = DataSource(
        name=data.name,
        platform=data.platform,
        config=data.config,
        is_active=data.is_active,
        schedule=data.schedule,
    )

    try:
        session.add(source)
        await session.commit()
        await session.refresh(source)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data source with name '{data.name}' already exists",
        )

    return DataSourceResponse(
        id=str(source.id),
        name=source.name,
        platform=source.platform,
        config=source.config or {},
        is_active=source.is_active,
        schedule=source.schedule,
        last_crawl_at=source.last_crawl_at.isoformat() if source.last_crawl_at else None,
        created_at=source.created_at.isoformat(),
        updated_at=source.updated_at.isoformat() if source.updated_at else None,
    )


@router.get("/{source_id}", response_model=DataSourceResponse)
async def get_source(session: DatabaseSession, source_id: str):
    """Get a specific data source by ID."""
    try:
        source_uuid = uuid.UUID(source_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid source ID format",
        )

    result = await session.execute(select(DataSource).where(DataSource.id == source_uuid))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {source_id} not found",
        )

    return DataSourceResponse(
        id=str(source.id),
        name=source.name,
        platform=source.platform,
        config=source.config or {},
        is_active=source.is_active,
        schedule=source.schedule,
        last_crawl_at=source.last_crawl_at.isoformat() if source.last_crawl_at else None,
        created_at=source.created_at.isoformat(),
        updated_at=source.updated_at.isoformat() if source.updated_at else None,
    )


@router.patch("/{source_id}", response_model=DataSourceResponse)
async def update_source(session: DatabaseSession, source_id: str, data: DataSourceUpdate):
    """Update a data source."""
    try:
        source_uuid = uuid.UUID(source_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid source ID format",
        )

    result = await session.execute(select(DataSource).where(DataSource.id == source_uuid))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {source_id} not found",
        )

    # Update fields
    if data.name is not None:
        source.name = data.name
    if data.config is not None:
        source.config = data.config
    if data.is_active is not None:
        source.is_active = data.is_active
    if data.schedule is not None:
        source.schedule = data.schedule

    await session.commit()
    await session.refresh(source)

    return DataSourceResponse(
        id=str(source.id),
        name=source.name,
        platform=source.platform,
        config=source.config or {},
        is_active=source.is_active,
        schedule=source.schedule,
        last_crawl_at=source.last_crawl_at.isoformat() if source.last_crawl_at else None,
        created_at=source.created_at.isoformat(),
        updated_at=source.updated_at.isoformat() if source.updated_at else None,
    )


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(session: DatabaseSession, source_id: str):
    """Delete a data source."""
    try:
        source_uuid = uuid.UUID(source_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid source ID format",
        )

    result = await session.execute(select(DataSource).where(DataSource.id == source_uuid))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {source_id} not found",
        )

    await session.delete(source)
    await session.commit()
