"""API endpoints for feedback management."""

from __future__ import annotations

import uuid

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import asc, func, or_, select

from voc_app.models import DataSource, Feedback

from .dependencies import DatabaseSession, Pagination, Sorting

router = APIRouter()


class FeedbackResponse(BaseModel):
    """Schema for feedback response."""

    id: str
    data_source_id: str
    crawl_run_id: str | None
    external_id: str | None
    author_handle: str | None
    raw_content: str
    clean_content: str | None
    language: str | None
    posted_at: str | None
    url: str | None
    created_at: str

    class Config:
        from_attributes = True


@router.get("", response_model=list[FeedbackResponse])
async def list_feedback(
    session: DatabaseSession,
    pagination: Pagination,
    sorting: Sorting,
    data_source_id: str | None = None,
    language: str | None = None,
    platform: str | None = None,
    keyword: str | None = Query(None, min_length=2, description="Search within feedback content"),
    posted_after: datetime | None = Query(None, description="Filter feedback posted after this timestamp"),
    posted_before: datetime | None = Query(None, description="Filter feedback posted before this timestamp"),
):
    """List feedback items with optional filtering."""
    query = select(Feedback)
    joined_source = False

    if data_source_id:
        try:
            source_uuid = uuid.UUID(data_source_id)
            query = query.where(Feedback.data_source_id == source_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid data_source_id format",
            )

    if language:
        query = query.where(Feedback.language == language)

    if platform:
        if not joined_source:
            query = query.join(DataSource, Feedback.data_source_id == DataSource.id)
            joined_source = True
        query = query.where(DataSource.platform == platform)

    if posted_after:
        query = query.where(Feedback.posted_at >= posted_after)

    if posted_before:
        query = query.where(Feedback.posted_at <= posted_before)

    if keyword:
        pattern = f"%{keyword.lower()}%"
        query = query.where(
            or_(
                func.lower(func.coalesce(Feedback.clean_content, "")).like(pattern),
                func.lower(func.coalesce(Feedback.raw_content, "")).like(pattern),
            )
        )

    sort_map = {
        "created_at": Feedback.created_at,
        "posted_at": Feedback.posted_at,
    }
    sort_column = sort_map.get(sorting.sort_by, Feedback.created_at)
    order_clause = sort_column.desc() if sorting.order == "desc" else asc(sort_column)

    query = query.order_by(order_clause)
    query = query.offset(pagination.skip).limit(pagination.limit)

    result = await session.execute(query)
    feedback_items = result.scalars().all()

    return [
        FeedbackResponse(
            id=str(item.id),
            data_source_id=str(item.data_source_id),
            crawl_run_id=str(item.crawl_run_id) if item.crawl_run_id else None,
            external_id=item.external_id,
            author_handle=item.author_handle,
            raw_content=item.raw_content,
            clean_content=item.clean_content,
            language=item.language,
            posted_at=item.posted_at.isoformat() if item.posted_at else None,
            url=item.url,
            created_at=item.created_at.isoformat(),
        )
        for item in feedback_items
    ]


@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(session: DatabaseSession, feedback_id: str):
    """Get a specific feedback item by ID."""
    try:
        feedback_uuid = uuid.UUID(feedback_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid feedback ID format",
        )

    result = await session.execute(select(Feedback).where(Feedback.id == feedback_uuid))
    feedback = result.scalar_one_or_none()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feedback {feedback_id} not found",
        )

    return FeedbackResponse(
        id=str(feedback.id),
        data_source_id=str(feedback.data_source_id),
        crawl_run_id=str(feedback.crawl_run_id) if feedback.crawl_run_id else None,
        external_id=feedback.external_id,
        author_handle=feedback.author_handle,
        raw_content=feedback.raw_content,
        clean_content=feedback.clean_content,
        language=feedback.language,
        posted_at=feedback.posted_at.isoformat() if feedback.posted_at else None,
        url=feedback.url,
        created_at=feedback.created_at.isoformat(),
    )
