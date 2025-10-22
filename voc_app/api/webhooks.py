"""API endpoints for webhook subscription management."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select

from voc_app.models import WebhookSubscription

from .dependencies import DatabaseSession

router = APIRouter()


class WebhookSubscriptionCreate(BaseModel):
    """Schema for creating a webhook subscription."""

    name: str
    url: HttpUrl
    secret: str | None = None
    event_types: dict | None = None
    description: str | None = None


class WebhookSubscriptionUpdate(BaseModel):
    """Schema for updating a webhook subscription."""

    name: str | None = None
    url: HttpUrl | None = None
    secret: str | None = None
    event_types: dict | None = None
    is_active: bool | None = None
    description: str | None = None


class WebhookSubscriptionResponse(BaseModel):
    """Schema for webhook subscription response."""

    id: str
    name: str
    url: str
    event_types: dict | None
    is_active: bool
    description: str | None
    last_triggered_at: str | None
    failure_count: int
    created_at: str

    class Config:
        from_attributes = True


@router.post("", response_model=WebhookSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook_subscription(
    subscription: WebhookSubscriptionCreate,
    session: DatabaseSession,
):
    """Create a new webhook subscription.
    
    Allows external systems to register endpoints for receiving webhook notifications.
    """
    new_subscription = WebhookSubscription(
        name=subscription.name,
        url=str(subscription.url),
        secret=subscription.secret,
        event_types=subscription.event_types or {"subscribed_events": ["alert.triggered"]},
        description=subscription.description,
    )
    
    session.add(new_subscription)
    await session.commit()
    await session.refresh(new_subscription)
    
    return WebhookSubscriptionResponse(
        id=str(new_subscription.id),
        name=new_subscription.name,
        url=new_subscription.url,
        event_types=new_subscription.event_types,
        is_active=new_subscription.is_active,
        description=new_subscription.description,
        last_triggered_at=new_subscription.last_triggered_at.isoformat() if new_subscription.last_triggered_at else None,
        failure_count=new_subscription.failure_count,
        created_at=new_subscription.created_at.isoformat(),
    )


@router.get("", response_model=list[WebhookSubscriptionResponse])
async def list_webhook_subscriptions(session: DatabaseSession):
    """List all webhook subscriptions."""
    result = await session.execute(select(WebhookSubscription))
    subscriptions = result.scalars().all()
    
    return [
        WebhookSubscriptionResponse(
            id=str(sub.id),
            name=sub.name,
            url=sub.url,
            event_types=sub.event_types,
            is_active=sub.is_active,
            description=sub.description,
            last_triggered_at=sub.last_triggered_at.isoformat() if sub.last_triggered_at else None,
            failure_count=sub.failure_count,
            created_at=sub.created_at.isoformat(),
        )
        for sub in subscriptions
    ]


@router.get("/{subscription_id}", response_model=WebhookSubscriptionResponse)
async def get_webhook_subscription(subscription_id: str, session: DatabaseSession):
    """Get a specific webhook subscription by ID."""
    try:
        sub_uuid = uuid.UUID(subscription_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid subscription ID format",
        )
    
    result = await session.execute(
        select(WebhookSubscription).where(WebhookSubscription.id == sub_uuid)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription {subscription_id} not found",
        )
    
    return WebhookSubscriptionResponse(
        id=str(subscription.id),
        name=subscription.name,
        url=subscription.url,
        event_types=subscription.event_types,
        is_active=subscription.is_active,
        description=subscription.description,
        last_triggered_at=subscription.last_triggered_at.isoformat() if subscription.last_triggered_at else None,
        failure_count=subscription.failure_count,
        created_at=subscription.created_at.isoformat(),
    )


@router.patch("/{subscription_id}", response_model=WebhookSubscriptionResponse)
async def update_webhook_subscription(
    subscription_id: str,
    updates: WebhookSubscriptionUpdate,
    session: DatabaseSession,
):
    """Update a webhook subscription."""
    try:
        sub_uuid = uuid.UUID(subscription_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid subscription ID format",
        )
    
    result = await session.execute(
        select(WebhookSubscription).where(WebhookSubscription.id == sub_uuid)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription {subscription_id} not found",
        )
    
    # Apply updates
    if updates.name is not None:
        subscription.name = updates.name
    if updates.url is not None:
        subscription.url = str(updates.url)
    if updates.secret is not None:
        subscription.secret = updates.secret
    if updates.event_types is not None:
        subscription.event_types = updates.event_types
    if updates.is_active is not None:
        subscription.is_active = updates.is_active
    if updates.description is not None:
        subscription.description = updates.description
    
    await session.commit()
    await session.refresh(subscription)
    
    return WebhookSubscriptionResponse(
        id=str(subscription.id),
        name=subscription.name,
        url=subscription.url,
        event_types=subscription.event_types,
        is_active=subscription.is_active,
        description=subscription.description,
        last_triggered_at=subscription.last_triggered_at.isoformat() if subscription.last_triggered_at else None,
        failure_count=subscription.failure_count,
        created_at=subscription.created_at.isoformat(),
    )


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook_subscription(subscription_id: str, session: DatabaseSession):
    """Delete a webhook subscription."""
    try:
        sub_uuid = uuid.UUID(subscription_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid subscription ID format",
        )
    
    result = await session.execute(
        select(WebhookSubscription).where(WebhookSubscription.id == sub_uuid)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription {subscription_id} not found",
        )
    
    await session.delete(subscription)
    await session.commit()
