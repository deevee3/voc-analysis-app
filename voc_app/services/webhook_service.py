"""Webhook dispatch service with retry logic."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from voc_app.models import WebhookSubscription

logger = logging.getLogger(__name__)


class WebhookService:
    """Handles webhook dispatch with retry and authentication."""

    MAX_RETRIES = 3
    TIMEOUT_SECONDS = 10

    @staticmethod
    def _generate_signature(payload: str, secret: str) -> str:
        """Generate HMAC signature for webhook payload.
        
        Args:
            payload: JSON payload string
            secret: Webhook secret key
            
        Returns:
            HMAC-SHA256 signature as hex string
        """
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

    @staticmethod
    async def dispatch_webhook(
        session: AsyncSession,
        subscription_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> bool:
        """Dispatch webhook to a subscribed endpoint.
        
        Args:
            session: Database session
            subscription_id: UUID string of webhook subscription
            event_type: Type of event (e.g., "alert.triggered", "insight.created")
            payload: Event data to send
            
        Returns:
            True if dispatch succeeded, False otherwise
        """
        import uuid as uuid_module
        
        # Convert string to UUID
        try:
            sub_uuid = uuid_module.UUID(subscription_id)
        except ValueError:
            logger.error(f"Invalid subscription_id format: {subscription_id}")
            return False
        
        # Fetch subscription
        result = await session.execute(
            select(WebhookSubscription).where(WebhookSubscription.id == sub_uuid)
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription or not subscription.is_active:
            logger.warning(f"Webhook subscription {subscription_id} not found or inactive")
            return False
        
        # Check if subscription is interested in this event type
        if subscription.event_types:
            if event_type not in subscription.event_types.get("subscribed_events", []):
                logger.debug(f"Subscription {subscription_id} not subscribed to {event_type}")
                return True  # Not an error, just not interested
        
        # Prepare payload
        webhook_payload = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": payload,
        }
        payload_json = json.dumps(webhook_payload)
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "VOC-App-Webhook/1.0",
        }
        
        # Add signature if secret is configured
        if subscription.secret:
            signature = WebhookService._generate_signature(payload_json, subscription.secret)
            headers["X-Webhook-Signature"] = f"sha256={signature}"
        
        # Attempt delivery with retries
        success = False
        last_error = None
        
        async with httpx.AsyncClient(timeout=WebhookService.TIMEOUT_SECONDS) as client:
            for attempt in range(WebhookService.MAX_RETRIES):
                try:
                    response = await client.post(
                        subscription.url,
                        content=payload_json,
                        headers=headers,
                    )
                    
                    if response.status_code in (200, 201, 202, 204):
                        success = True
                        logger.info(
                            f"Webhook delivered to {subscription.name} "
                            f"(attempt {attempt + 1}/{WebhookService.MAX_RETRIES})"
                        )
                        break
                    else:
                        last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                        logger.warning(
                            f"Webhook delivery failed to {subscription.name}: {last_error}"
                        )
                
                except httpx.RequestError as e:
                    last_error = str(e)
                    logger.warning(
                        f"Webhook request error to {subscription.name} "
                        f"(attempt {attempt + 1}/{WebhookService.MAX_RETRIES}): {e}"
                    )
                
                except Exception as e:
                    last_error = str(e)
                    logger.error(
                        f"Unexpected error dispatching webhook to {subscription.name}: {e}",
                        exc_info=True
                    )
        
        # Update subscription metadata
        if success:
            await session.execute(
                update(WebhookSubscription)
                .where(WebhookSubscription.id == sub_uuid)
                .values(
                    last_triggered_at=datetime.utcnow(),
                    failure_count=0,
                )
            )
        else:
            await session.execute(
                update(WebhookSubscription)
                .where(WebhookSubscription.id == sub_uuid)
                .values(
                    failure_count=subscription.failure_count + 1,
                )
            )
            logger.error(
                f"Webhook delivery failed after {WebhookService.MAX_RETRIES} attempts "
                f"to {subscription.name}: {last_error}"
            )
        
        await session.commit()
        return success

    @staticmethod
    async def dispatch_to_all_subscribers(
        session: AsyncSession,
        event_type: str,
        payload: dict[str, Any],
    ) -> int:
        """Dispatch webhook to all active subscribers for an event type.
        
        Args:
            session: Database session
            event_type: Type of event
            payload: Event data
            
        Returns:
            Number of successful dispatches
        """
        # Fetch all active subscriptions
        result = await session.execute(
            select(WebhookSubscription).where(WebhookSubscription.is_active == True)
        )
        subscriptions = result.scalars().all()
        
        success_count = 0
        for subscription in subscriptions:
            if await WebhookService.dispatch_webhook(
                session, str(subscription.id), event_type, payload
            ):
                success_count += 1
        
        return success_count
