"""API endpoints for theme management."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from voc_app.models import Theme

from .dependencies import DatabaseSession, Pagination

router = APIRouter()


class ThemeCreate(BaseModel):
    """Schema for creating a theme."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    is_system: bool = False


class ThemeUpdate(BaseModel):
    """Schema for updating a theme."""

    name: str | None = None
    description: str | None = None


class ThemeResponse(BaseModel):
    """Schema for theme response."""

    id: str
    name: str
    description: str | None
    is_system: bool
    created_at: str

    class Config:
        from_attributes = True


@router.get("", response_model=list[ThemeResponse])
async def list_themes(
    session: DatabaseSession,
    pagination: Pagination,
    is_system: bool | None = None,
):
    """List themes with optional filtering."""
    query = select(Theme).order_by(Theme.name)

    if is_system is not None:
        query = query.where(Theme.is_system == is_system)

    query = query.offset(pagination.skip).limit(pagination.limit)

    result = await session.execute(query)
    themes = result.scalars().all()

    return [
        ThemeResponse(
            id=str(theme.id),
            name=theme.name,
            description=theme.description,
            is_system=theme.is_system,
            created_at=theme.created_at.isoformat(),
        )
        for theme in themes
    ]


@router.post("", response_model=ThemeResponse, status_code=status.HTTP_201_CREATED)
async def create_theme(session: DatabaseSession, data: ThemeCreate):
    """Create a new theme."""
    theme = Theme(
        name=data.name,
        description=data.description,
        is_system=data.is_system,
    )

    try:
        session.add(theme)
        await session.commit()
        await session.refresh(theme)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Theme with name '{data.name}' already exists",
        )

    return ThemeResponse(
        id=str(theme.id),
        name=theme.name,
        description=theme.description,
        is_system=theme.is_system,
        created_at=theme.created_at.isoformat(),
    )


@router.get("/{theme_id}", response_model=ThemeResponse)
async def get_theme(session: DatabaseSession, theme_id: str):
    """Get a specific theme by ID."""
    try:
        theme_uuid = uuid.UUID(theme_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid theme ID format",
        )

    result = await session.execute(select(Theme).where(Theme.id == theme_uuid))
    theme = result.scalar_one_or_none()

    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Theme {theme_id} not found",
        )

    return ThemeResponse(
        id=str(theme.id),
        name=theme.name,
        description=theme.description,
        is_system=theme.is_system,
        created_at=theme.created_at.isoformat(),
    )


@router.patch("/{theme_id}", response_model=ThemeResponse)
async def update_theme(session: DatabaseSession, theme_id: str, data: ThemeUpdate):
    """Update a theme."""
    try:
        theme_uuid = uuid.UUID(theme_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid theme ID format",
        )

    result = await session.execute(select(Theme).where(Theme.id == theme_uuid))
    theme = result.scalar_one_or_none()

    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Theme {theme_id} not found",
        )

    if theme.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify system themes",
        )

    if data.name is not None:
        theme.name = data.name
    if data.description is not None:
        theme.description = data.description

    await session.commit()
    await session.refresh(theme)

    return ThemeResponse(
        id=str(theme.id),
        name=theme.name,
        description=theme.description,
        is_system=theme.is_system,
        created_at=theme.created_at.isoformat(),
    )


@router.delete("/{theme_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_theme(session: DatabaseSession, theme_id: str):
    """Delete a theme."""
    try:
        theme_uuid = uuid.UUID(theme_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid theme ID format",
        )

    result = await session.execute(select(Theme).where(Theme.id == theme_uuid))
    theme = result.scalar_one_or_none()

    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Theme {theme_id} not found",
        )

    if theme.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete system themes",
        )

    await session.delete(theme)
    await session.commit()
