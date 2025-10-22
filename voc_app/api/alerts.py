"""API endpoints for alert management."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from voc_app.models import AlertEvent, AlertRule

from .dependencies import DatabaseSession, Pagination

router = APIRouter()


class AlertRuleCreate(BaseModel):
    """Schema for creating an alert rule."""

    name: str = Field(..., min_length=1, max_length=255)
    rule_type: str = Field(..., min_length=1, max_length=50)
    threshold_value: float | None = None
    keywords: dict[str, Any] | None = None
    competitor_filters: dict[str, Any] | None = None
    channels: dict[str, Any] | None = None
    enabled: bool = True


class AlertRuleUpdate(BaseModel):
    """Schema for updating an alert rule."""

    name: str | None = None
    threshold_value: float | None = None
    keywords: dict[str, Any] | None = None
    competitor_filters: dict[str, Any] | None = None
    channels: dict[str, Any] | None = None
    enabled: bool | None = None


class AlertRuleResponse(BaseModel):
    """Schema for alert rule response."""

    id: str
    name: str
    rule_type: str
    threshold_value: float | None
    keywords: dict[str, Any] | None
    competitor_filters: dict[str, Any] | None
    channels: dict[str, Any] | None
    enabled: bool
    created_at: str

    class Config:
        from_attributes = True


class AlertEventResponse(BaseModel):
    """Schema for alert event response."""

    id: str
    alert_rule_id: str
    primary_insight_id: str | None
    triggered_at: str
    severity: str
    status: str
    payload: dict[str, Any] | None
    resolved_at: str | None

    class Config:
        from_attributes = True


@router.get("/rules", response_model=list[AlertRuleResponse])
async def list_alert_rules(
    session: DatabaseSession,
    pagination: Pagination,
    enabled: bool | None = None,
    rule_type: str | None = None,
):
    """List alert rules with optional filtering."""
    query = select(AlertRule).order_by(AlertRule.created_at.desc())

    if enabled is not None:
        query = query.where(AlertRule.enabled == enabled)

    if rule_type:
        query = query.where(AlertRule.rule_type == rule_type)

    query = query.offset(pagination.skip).limit(pagination.limit)

    result = await session.execute(query)
    rules = result.scalars().all()

    return [
        AlertRuleResponse(
            id=str(rule.id),
            name=rule.name,
            rule_type=rule.rule_type,
            threshold_value=rule.threshold_value,
            keywords=rule.keywords,
            competitor_filters=rule.competitor_filters,
            channels=rule.channels,
            enabled=rule.enabled,
            created_at=rule.created_at.isoformat(),
        )
        for rule in rules
    ]


@router.post("/rules", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(session: DatabaseSession, data: AlertRuleCreate):
    """Create a new alert rule."""
    rule = AlertRule(
        name=data.name,
        rule_type=data.rule_type,
        threshold_value=data.threshold_value,
        keywords=data.keywords,
        competitor_filters=data.competitor_filters,
        channels=data.channels,
        enabled=data.enabled,
    )

    try:
        session.add(rule)
        await session.commit()
        await session.refresh(rule)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Alert rule with name '{data.name}' already exists",
        )

    return AlertRuleResponse(
        id=str(rule.id),
        name=rule.name,
        rule_type=rule.rule_type,
        threshold_value=rule.threshold_value,
        keywords=rule.keywords,
        competitor_filters=rule.competitor_filters,
        channels=rule.channels,
        enabled=rule.enabled,
        created_at=rule.created_at.isoformat(),
    )


@router.get("/rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(session: DatabaseSession, rule_id: str):
    """Get a specific alert rule by ID."""
    try:
        rule_uuid = uuid.UUID(rule_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid rule ID format",
        )

    result = await session.execute(select(AlertRule).where(AlertRule.id == rule_uuid))
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert rule {rule_id} not found",
        )

    return AlertRuleResponse(
        id=str(rule.id),
        name=rule.name,
        rule_type=rule.rule_type,
        threshold_value=rule.threshold_value,
        keywords=rule.keywords,
        competitor_filters=rule.competitor_filters,
        channels=rule.channels,
        enabled=rule.enabled,
        created_at=rule.created_at.isoformat(),
    )


@router.patch("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(session: DatabaseSession, rule_id: str, data: AlertRuleUpdate):
    """Update an alert rule."""
    try:
        rule_uuid = uuid.UUID(rule_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid rule ID format",
        )

    result = await session.execute(select(AlertRule).where(AlertRule.id == rule_uuid))
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert rule {rule_id} not found",
        )

    if data.name is not None:
        rule.name = data.name
    if data.threshold_value is not None:
        rule.threshold_value = data.threshold_value
    if data.keywords is not None:
        rule.keywords = data.keywords
    if data.competitor_filters is not None:
        rule.competitor_filters = data.competitor_filters
    if data.channels is not None:
        rule.channels = data.channels
    if data.enabled is not None:
        rule.enabled = data.enabled

    await session.commit()
    await session.refresh(rule)

    return AlertRuleResponse(
        id=str(rule.id),
        name=rule.name,
        rule_type=rule.rule_type,
        threshold_value=rule.threshold_value,
        keywords=rule.keywords,
        competitor_filters=rule.competitor_filters,
        channels=rule.channels,
        enabled=rule.enabled,
        created_at=rule.created_at.isoformat(),
    )


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_rule(session: DatabaseSession, rule_id: str):
    """Delete an alert rule."""
    try:
        rule_uuid = uuid.UUID(rule_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid rule ID format",
        )

    result = await session.execute(select(AlertRule).where(AlertRule.id == rule_uuid))
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert rule {rule_id} not found",
        )

    await session.delete(rule)
    await session.commit()


@router.get("/events", response_model=list[AlertEventResponse])
async def list_alert_events(
    session: DatabaseSession,
    pagination: Pagination,
    status_filter: str | None = None,
    severity: str | None = None,
):
    """List alert events with optional filtering."""
    query = select(AlertEvent).order_by(AlertEvent.triggered_at.desc())

    if status_filter:
        query = query.where(AlertEvent.status == status_filter)

    if severity:
        query = query.where(AlertEvent.severity == severity)

    query = query.offset(pagination.skip).limit(pagination.limit)

    result = await session.execute(query)
    events = result.scalars().all()

    return [
        AlertEventResponse(
            id=str(event.id),
            alert_rule_id=str(event.alert_rule_id),
            primary_insight_id=str(event.primary_insight_id) if event.primary_insight_id else None,
            triggered_at=event.triggered_at.isoformat(),
            severity=event.severity,
            status=event.status,
            payload=event.payload,
            resolved_at=event.resolved_at.isoformat() if event.resolved_at else None,
        )
        for event in events
    ]


@router.get("/events/{event_id}", response_model=AlertEventResponse)
async def get_alert_event(session: DatabaseSession, event_id: str):
    """Get a specific alert event by ID."""
    try:
        event_uuid = uuid.UUID(event_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid event ID format",
        )

    result = await session.execute(select(AlertEvent).where(AlertEvent.id == event_uuid))
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert event {event_id} not found",
        )

    return AlertEventResponse(
        id=str(event.id),
        alert_rule_id=str(event.alert_rule_id),
        primary_insight_id=str(event.primary_insight_id) if event.primary_insight_id else None,
        triggered_at=event.triggered_at.isoformat(),
        severity=event.severity,
        status=event.status,
        payload=event.payload,
        resolved_at=event.resolved_at.isoformat() if event.resolved_at else None,
    )


@router.post("/events/{event_id}/resolve", response_model=AlertEventResponse)
async def resolve_alert_event(session: DatabaseSession, event_id: str):
    """Mark an alert event as resolved."""
    try:
        event_uuid = uuid.UUID(event_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid event ID format",
        )

    result = await session.execute(select(AlertEvent).where(AlertEvent.id == event_uuid))
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert event {event_id} not found",
        )

    from datetime import datetime

    event.status = "resolved"
    event.resolved_at = datetime.utcnow()

    await session.commit()
    await session.refresh(event)

    return AlertEventResponse(
        id=str(event.id),
        alert_rule_id=str(event.alert_rule_id),
        primary_insight_id=str(event.primary_insight_id) if event.primary_insight_id else None,
        triggered_at=event.triggered_at.isoformat(),
        severity=event.severity,
        status=event.status,
        payload=event.payload,
        resolved_at=event.resolved_at.isoformat() if event.resolved_at else None,
    )
