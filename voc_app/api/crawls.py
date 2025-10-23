"""API endpoints for crawl run management."""

from __future__ import annotations

import uuid
from typing import Any

from kombu.exceptions import OperationalError

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from voc_app.models import CrawlRun, DataSource
from voc_app.tasks.crawl_tasks import execute_crawl

from .dependencies import DatabaseSession, Pagination


class CrawlTriggerRequest(BaseModel):
    """Schema for triggering a manual crawl."""

    data_source_id: str = Field(..., description="ID of the data source to crawl")
    query_override: dict[str, str] | None = Field(
        default=None,
        description="Optional overrides such as query/subreddit for the crawl",
    )


class CrawlTriggerResponse(BaseModel):
    """Schema for manual crawl trigger response."""

    task_id: str

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


def _validate_manual_crawl_config(data_source: DataSource, override: dict[str, str] | None) -> dict[str, Any] | None:
    """Ensure manual crawls have the configuration they need."""

    base_config: dict[str, Any] = dict(data_source.config or {})
    merged_override: dict[str, Any] | None = None

    if override:
        # Filter out empty override values and merge over base config
        merged_override = {**base_config, **{k: v for k, v in override.items() if v}}
    else:
        merged_override = base_config

    platform = data_source.platform.lower()

    if platform == "reddit":
        subreddit = merged_override.get("subreddit") or merged_override.get("query")
        if not subreddit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reddit sources require a 'subreddit' or 'query' value before running a crawl.",
            )
    elif platform == "twitter":
        if not merged_override.get("query"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Twitter sources require a 'query' keyword before running a crawl.",
            )
    elif platform == "youtube":
        if not (merged_override.get("video_id") or merged_override.get("channel_id")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="YouTube sources require a 'video_id' or 'channel_id' before running a crawl.",
            )
    elif platform == "trustpilot":
        if not merged_override.get("company_name"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trustpilot sources require a 'company_name' before running a crawl.",
            )
    elif platform == "quora":
        if not merged_override.get("query"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quora sources require a 'query' term before running a crawl.",
            )
    elif platform == "g2":
        if not merged_override.get("product_slug"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="G2 sources require a 'product_slug' before running a crawl.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Manual crawl triggering is not yet supported for platform '{data_source.platform}'.",
        )

    # Only pass overrides to the task if the caller supplied them; otherwise allow the task to read the saved config
    if override:
        return merged_override
    return None


@router.post("/trigger", response_model=CrawlTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_crawl(payload: CrawlTriggerRequest, session: DatabaseSession) -> CrawlTriggerResponse:
    """Trigger a background crawl for the given data source."""

    try:
        data_source_uuid = uuid.UUID(payload.data_source_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data_source_id format",
        )

    result = await session.execute(
        select(DataSource).where(DataSource.id == data_source_uuid)
    )
    data_source = result.scalar_one_or_none()

    if not data_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {payload.data_source_id} not found",
        )

    if not data_source.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data source is paused. Activate it before running a crawl.",
        )

    override_payload = _validate_manual_crawl_config(data_source, payload.query_override)

    try:
        async_result = execute_crawl.delay(payload.data_source_id, override_payload)
    except OperationalError as exc:  # Broker/worker not available
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to enqueue crawl. Ensure the Celery worker and Redis broker are running.",
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue crawl task",
        ) from exc

    return CrawlTriggerResponse(task_id=str(async_result.id))
