"""Tests for webhook functionality."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from voc_app.main import app
from voc_app.models import WebhookSubscription
from voc_app.services.webhook_service import WebhookService
from voc_app.tests.test_api import TestingSessionLocal, setup_test_db  # noqa: F401

client = TestClient(app)


class TestWebhookEndpoints:
    """Test webhook subscription API endpoints."""

    @pytest.mark.asyncio
    async def test_create_webhook_subscription(self):
        """Test creating a new webhook subscription."""
        payload = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "secret": "test_secret_123",
            "event_types": {"subscribed_events": ["alert.triggered", "insight.created"]},
            "description": "Test webhook for alerts",
        }

        response = client.post("/api/v1/webhooks", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Webhook"
        assert data["url"] == "https://example.com/webhook"
        assert data["is_active"] is True
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_webhook_subscriptions(self):
        """Test listing webhook subscriptions."""
        # Create a subscription first
        async with TestingSessionLocal() as session:
            subscription = WebhookSubscription(
                name="List Test Webhook",
                url="https://example.com/webhook",
                is_active=True,
            )
            session.add(subscription)
            await session.commit()

        response = client.get("/api/v1/webhooks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_webhook_subscription(self):
        """Test getting a specific webhook subscription."""
        async with TestingSessionLocal() as session:
            subscription = WebhookSubscription(
                name="Get Test Webhook",
                url="https://example.com/webhook",
                is_active=True,
            )
            session.add(subscription)
            await session.commit()
            await session.refresh(subscription)
            subscription_id = str(subscription.id)

        response = client.get(f"/api/v1/webhooks/{subscription_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == subscription_id
        assert data["name"] == "Get Test Webhook"

    @pytest.mark.asyncio
    async def test_update_webhook_subscription(self):
        """Test updating a webhook subscription."""
        async with TestingSessionLocal() as session:
            subscription = WebhookSubscription(
                name="Update Test Webhook",
                url="https://example.com/webhook",
                is_active=True,
            )
            session.add(subscription)
            await session.commit()
            await session.refresh(subscription)
            subscription_id = str(subscription.id)

        payload = {"name": "Updated Webhook", "is_active": False}
        response = client.patch(f"/api/v1/webhooks/{subscription_id}", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Webhook"
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_webhook_subscription(self):
        """Test deleting a webhook subscription."""
        async with TestingSessionLocal() as session:
            subscription = WebhookSubscription(
                name="Delete Test Webhook",
                url="https://example.com/webhook",
                is_active=True,
            )
            session.add(subscription)
            await session.commit()
            await session.refresh(subscription)
            subscription_id = str(subscription.id)

        response = client.delete(f"/api/v1/webhooks/{subscription_id}")
        assert response.status_code == 204


class TestWebhookService:
    """Test webhook dispatch service."""

    @pytest.mark.asyncio
    async def test_generate_signature(self):
        """Test HMAC signature generation."""
        payload = '{"test": "data"}'
        secret = "test_secret"
        
        signature = WebhookService._generate_signature(payload, secret)
        
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex digest length

    @pytest.mark.asyncio
    async def test_dispatch_webhook_success(self):
        """Test successful webhook dispatch."""
        async with TestingSessionLocal() as session:
            subscription = WebhookSubscription(
                name="Dispatch Test",
                url="https://example.com/webhook",
                secret="test_secret",
                event_types={"subscribed_events": ["alert.triggered"]},
                is_active=True,
            )
            session.add(subscription)
            await session.commit()
            await session.refresh(subscription)
            subscription_id = str(subscription.id)

        # Mock httpx client
        with patch("voc_app.services.webhook_service.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            async with TestingSessionLocal() as session:
                success = await WebhookService.dispatch_webhook(
                    session,
                    subscription_id,
                    "alert.triggered",
                    {"alert_id": "test-123", "severity": "high"},
                )

            assert success is True

    @pytest.mark.asyncio
    async def test_dispatch_webhook_failure(self):
        """Test webhook dispatch with failure."""
        async with TestingSessionLocal() as session:
            subscription = WebhookSubscription(
                name="Failure Test",
                url="https://example.com/webhook",
                is_active=True,
            )
            session.add(subscription)
            await session.commit()
            await session.refresh(subscription)
            subscription_id = str(subscription.id)

        # Mock httpx client to return error
        with patch("voc_app.services.webhook_service.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            async with TestingSessionLocal() as session:
                success = await WebhookService.dispatch_webhook(
                    session,
                    subscription_id,
                    "alert.triggered",
                    {"test": "data"},
                )

            assert success is False

    @pytest.mark.asyncio
    async def test_dispatch_to_all_subscribers(self):
        """Test dispatching to all active subscribers."""
        async with TestingSessionLocal() as session:
            # Create multiple subscriptions
            sub1 = WebhookSubscription(
                name="Subscriber 1",
                url="https://example.com/webhook1",
                is_active=True,
            )
            sub2 = WebhookSubscription(
                name="Subscriber 2",
                url="https://example.com/webhook2",
                is_active=True,
            )
            sub3 = WebhookSubscription(
                name="Inactive Subscriber",
                url="https://example.com/webhook3",
                is_active=False,
            )
            session.add_all([sub1, sub2, sub3])
            await session.commit()

        # Mock successful dispatch
        with patch("voc_app.services.webhook_service.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            async with TestingSessionLocal() as session:
                count = await WebhookService.dispatch_to_all_subscribers(
                    session,
                    "test.event",
                    {"data": "test"},
                )

            # Should dispatch to at least 2 active subscribers (may include others from previous tests)
            assert count >= 2
