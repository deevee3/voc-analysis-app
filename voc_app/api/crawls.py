"""API endpoints for crawl run management."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from voc_app.models import CrawlRun

from .dependencies import DatabaseSession, Pagination

router = APIRouter()


class CrawlRunResponse(BaseModel):
    """Schema for crawl run response."""

    id: str
    data_source_id: str
    started_at: str
    finished_at: str | None
    status: str
    stats: dict[str, Any] | None

    class Config:
        from_attributes = True


@router.get("", response_model=list[CrawlRunResponse])
async def list_crawl_runs(
    session: DatabaseSession,
    pagination: Pagination,
    data_source_id: str | None = None,
    status_filter: str | None = None,
):
    """List crawl runs with optional filtering."""
    query = select(CrawlRun).order_by(CrawlRun.started_at.desc())

    if data_source_id:
        try:
            source_uuid = uuid.UUID(data_source_id)
            query = query.where(CrawlRun.data_source_id == source_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid data_source_id format",
            )

    if status_filter:
        query = query.where(CrawlRun.status == status_filter)

    query = query.offset(pagination.skip).limit(pagination.limit)

    result = await session.execute(query)
    crawl_runs = result.scalars().all()

    return [
        CrawlRunResponse(
            id=str(run.id),
            data_source_id=str(run.data_source_id),
            started_at=run.started_at.isoformat(),
            finished_at=run.finished_at.isoformat() if run.finished_at else None,
            status=run.status,
            stats=run.stats,
        )
        for run in crawl_runs
    ]


@router.get("/{crawl_id}", response_model=CrawlRunResponse)
async def get_crawl_run(session: DatabaseSession, crawl_id: str):
    """Get a specific crawl run by ID."""
    try:
        crawl_uuid = uuid.UUID(crawl_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid crawl ID format",
        )

    result = await session.execute(select(CrawlRun).where(CrawlRun.id == crawl_uuid))
    crawl_run = result.scalar_one_or_none()

    if not crawl_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crawl run {crawl_id} not found",
        )

    return CrawlRunResponse(
        id=str(crawl_run.id),
        data_source_id=str(crawl_run.data_source_id),
        started_at=crawl_run.started_at.isoformat(),
        finished_at=crawl_run.finished_at.isoformat() if crawl_run.finished_at else None,
        status=crawl_run.status,
        stats=crawl_run.stats,
    )
