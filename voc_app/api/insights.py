"""API endpoints for insights management."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import asc, func, select

from voc_app.models import (
    DataSource,
    Feedback,
    Insight,
    InsightThemeLink,
    Theme,
)

from .dependencies import DatabaseSession, Pagination, Sorting

router = APIRouter()


class InsightResponse(BaseModel):
    """Schema for insight response."""

    id: str
    feedback_id: str
    sentiment_score: float | None
    sentiment_label: str | None
    summary: str
    pain_points: list[dict[str, Any]] | None
    feature_requests: list[dict[str, Any]] | None
    competitor_mentions: list[dict[str, Any]] | None
    customer_context: dict[str, Any] | None
    journey_stage: str | None
    urgency_level: int | None
    created_at: str

    class Config:
        from_attributes = True


@router.get("", response_model=list[InsightResponse])
async def list_insights(
    session: DatabaseSession,
    pagination: Pagination,
    sorting: Sorting,
    feedback_id: str | None = None,
    data_source_id: str | None = None,
    platform: str | None = None,
    language: str | None = None,
    theme_id: str | None = None,
    theme_name: str | None = None,
    journey_stage: str | None = None,
    sentiment_label: str | None = None,
    min_sentiment: float | None = None,
    max_sentiment: float | None = None,
    min_urgency: int | None = None,
    max_urgency: int | None = None,
    created_after: datetime | None = Query(None, description="Filter insights created after this timestamp"),
    created_before: datetime | None = Query(None, description="Filter insights created before this timestamp"),
    posted_after: datetime | None = Query(None, description="Filter by feedback posted after this timestamp"),
    posted_before: datetime | None = Query(None, description="Filter by feedback posted before this timestamp"),
    keyword: str | None = Query(None, min_length=2, description="Search within insight summary"),
):
    """List insights with optional filtering."""
    query = select(Insight)
    joined_feedback = False
    needs_distinct = False

    if feedback_id:
        try:
            feedback_uuid = uuid.UUID(feedback_id)
            query = query.where(Insight.feedback_id == feedback_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid feedback_id format",
            )

    if data_source_id:
        try:
            source_uuid = uuid.UUID(data_source_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid data_source_id format",
            )
        if not joined_feedback:
            query = query.join(Feedback, Insight.feedback_id == Feedback.id)
            joined_feedback = True
        query = query.where(Feedback.data_source_id == source_uuid)

    if platform:
        if not joined_feedback:
            query = query.join(Feedback, Insight.feedback_id == Feedback.id)
            joined_feedback = True
        query = query.join(DataSource, Feedback.data_source_id == DataSource.id)
        needs_distinct = True
        query = query.where(DataSource.platform == platform)

    if language:
        if not joined_feedback:
            query = query.join(Feedback, Insight.feedback_id == Feedback.id)
            joined_feedback = True
        query = query.where(Feedback.language == language)

    if posted_after or posted_before:
        if not joined_feedback:
            query = query.join(Feedback, Insight.feedback_id == Feedback.id)
            joined_feedback = True
        if posted_after:
            query = query.where(Feedback.posted_at >= posted_after)
        if posted_before:
            query = query.where(Feedback.posted_at <= posted_before)

    if theme_id or theme_name:
        query = query.join(InsightThemeLink, Insight.id == InsightThemeLink.insight_id)
        needs_distinct = True
        if theme_id:
            try:
                theme_uuid = uuid.UUID(theme_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid theme_id format",
                )
            query = query.where(InsightThemeLink.theme_id == theme_uuid)
        if theme_name:
            query = query.join(Theme, InsightThemeLink.theme_id == Theme.id)
            query = query.where(Theme.name == theme_name)

    if journey_stage:
        query = query.where(Insight.journey_stage == journey_stage)

    if sentiment_label:
        query = query.where(Insight.sentiment_label == sentiment_label)

    if min_sentiment is not None:
        query = query.where(Insight.sentiment_score >= min_sentiment)

    if max_sentiment is not None:
        query = query.where(Insight.sentiment_score <= max_sentiment)

    if min_urgency is not None:
        query = query.where(Insight.urgency_level >= min_urgency)

    if max_urgency is not None:
        query = query.where(Insight.urgency_level <= max_urgency)

    if created_after:
        query = query.where(Insight.created_at >= created_after)

    if created_before:
        query = query.where(Insight.created_at <= created_before)

    if keyword:
        # Fallback to LIKE pattern matching (FTS5 requires raw SQL or custom function)
        pattern = f"%{keyword.lower()}%"
        query = query.where(
            func.lower(func.coalesce(Insight.summary, "")).like(pattern)
        )

    if needs_distinct:
        query = query.distinct()

    sort_map = {
        "created_at": Insight.created_at,
        "sentiment_score": Insight.sentiment_score,
        "urgency_level": Insight.urgency_level,
        "posted_at": Feedback.posted_at if joined_feedback else Insight.created_at,
    }

    sort_column = sort_map.get(sorting.sort_by, Insight.created_at)
    if sort_column is Feedback.posted_at and not joined_feedback:
        query = query.join(Feedback, Insight.feedback_id == Feedback.id)
        joined_feedback = True
        needs_distinct = True
    order_clause = sort_column.desc() if sorting.order == "desc" else asc(sort_column)

    query = query.order_by(order_clause)
    query = query.offset(pagination.skip).limit(pagination.limit)

    result = await session.execute(query)
    insights = result.scalars().all()

    return [
        InsightResponse(
            id=str(insight.id),
            feedback_id=str(insight.feedback_id),
            sentiment_score=insight.sentiment_score,
            sentiment_label=insight.sentiment_label,
            summary=insight.summary,
            pain_points=insight.pain_points,
            feature_requests=insight.feature_requests,
            competitor_mentions=insight.competitor_mentions,
            customer_context=insight.customer_context,
            journey_stage=insight.journey_stage,
            urgency_level=insight.urgency_level,
            created_at=insight.created_at.isoformat(),
        )
        for insight in insights
    ]


@router.get("/{insight_id}", response_model=InsightResponse)
async def get_insight(session: DatabaseSession, insight_id: str):
    """Get a specific insight by ID."""
    try:
        insight_uuid = uuid.UUID(insight_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid insight ID format",
        )

    result = await session.execute(select(Insight).where(Insight.id == insight_uuid))
    insight = result.scalar_one_or_none()

    if not insight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Insight {insight_id} not found",
        )

    return InsightResponse(
        id=str(insight.id),
        feedback_id=str(insight.feedback_id),
        sentiment_score=insight.sentiment_score,
        sentiment_label=insight.sentiment_label,
        summary=insight.summary,
        pain_points=insight.pain_points,
        feature_requests=insight.feature_requests,
        competitor_mentions=insight.competitor_mentions,
        customer_context=insight.customer_context,
        journey_stage=insight.journey_stage,
        urgency_level=insight.urgency_level,
        created_at=insight.created_at.isoformat(),
    )
