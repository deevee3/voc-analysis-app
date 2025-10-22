"""Tests for alert detection and notifications."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from voc_app.models import AlertRule, Insight
from voc_app.services.alert_service import AlertService


class TestAlertService:
    """Test suite for AlertService."""

    @pytest.mark.asyncio
    async def test_evaluate_rules_with_sentiment_threshold(self):
        """Test sentiment threshold rule evaluation."""
        mock_session = AsyncMock()
        service = AlertService(mock_session)

        # Create test data
        rule = AlertRule(
            id=uuid.uuid4(),
            name="Negative Sentiment Alert",
            rule_type="sentiment_threshold",
            threshold_value=-0.5,
            enabled=True,
        )

        insights = [
            Insight(
                id=uuid.uuid4(),
                feedback_id=uuid.uuid4(),
                summary="Customer is unhappy",
                sentiment_score=-0.8,
            ),
            Insight(
                id=uuid.uuid4(),
                feedback_id=uuid.uuid4(),
                summary="Product works well",
                sentiment_score=0.7,
            ),
        ]

        summary = await service.evaluate_rules(insights, [rule])

        assert summary.rules_evaluated == 1
        assert summary.alerts_triggered >= 0
        assert len(summary.trigger_results) == 1

    @pytest.mark.asyncio
    async def test_evaluate_rules_with_keyword_match(self):
        """Test keyword-based rule evaluation."""
        mock_session = AsyncMock()
        service = AlertService(mock_session)

        rule = AlertRule(
            id=uuid.uuid4(),
            name="Crash Detection",
            rule_type="keyword",
            keywords={"terms": ["crash", "error", "bug"]},
            enabled=True,
        )

        insights = [
            Insight(
                id=uuid.uuid4(),
                feedback_id=uuid.uuid4(),
                summary="The app crashes on startup",
            ),
            Insight(
                id=uuid.uuid4(),
                feedback_id=uuid.uuid4(),
                summary="Everything works fine",
            ),
        ]

        summary = await service.evaluate_rules(insights, [rule])

        assert summary.rules_evaluated == 1
        # At least one insight should match
        trigger_result = summary.trigger_results[0]
        assert len(trigger_result.matching_insights) >= 1

    @pytest.mark.asyncio
    async def test_evaluate_rules_with_urgency(self):
        """Test urgency-based rule evaluation."""
        mock_session = AsyncMock()
        service = AlertService(mock_session)

        rule = AlertRule(
            id=uuid.uuid4(),
            name="High Urgency Alert",
            rule_type="urgency",
            threshold_value=4,
            enabled=True,
        )

        insights = [
            Insight(
                id=uuid.uuid4(),
                feedback_id=uuid.uuid4(),
                summary="Critical issue",
                urgency_level=5,
            ),
            Insight(
                id=uuid.uuid4(),
                feedback_id=uuid.uuid4(),
                summary="Minor feedback",
                urgency_level=2,
            ),
        ]

        summary = await service.evaluate_rules(insights, [rule])

        assert summary.rules_evaluated == 1
        trigger_result = summary.trigger_results[0]
        assert len(trigger_result.matching_insights) >= 1
        assert trigger_result.matching_insights[0].urgency_level >= 4

    @pytest.mark.asyncio
    async def test_calculate_severity_critical(self):
        """Test severity calculation for critical alerts."""
        mock_session = AsyncMock()
        service = AlertService(mock_session)

        rule = AlertRule(
            id=uuid.uuid4(),
            name="Test Rule",
            rule_type="sentiment_threshold",
            enabled=True,
        )

        insights = [
            Insight(
                id=uuid.uuid4(),
                feedback_id=uuid.uuid4(),
                summary="Very negative",
                sentiment_score=-0.9,
            ),
            Insight(
                id=uuid.uuid4(),
                feedback_id=uuid.uuid4(),
                summary="Extremely negative",
                sentiment_score=-0.95,
            ),
        ]

        severity = service._calculate_severity(rule, insights)
        assert severity == "critical"

    @pytest.mark.asyncio
    async def test_get_active_alerts(self):
        """Test retrieving active alerts."""
        mock_session = AsyncMock()
        service = AlertService(mock_session)

        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        alerts = await service.get_active_alerts(limit=10)
        assert isinstance(alerts, list)

    @pytest.mark.asyncio
    async def test_resolve_alert(self):
        """Test resolving an alert."""
        mock_session = AsyncMock()
        service = AlertService(mock_session)

        alert_id = str(uuid.uuid4())
        mock_alert = MagicMock()
        mock_alert.id = alert_id
        mock_alert.status = "open"

        mock_session.execute.return_value.scalar_one.return_value = mock_alert

        resolved_alert = await service.resolve_alert(alert_id, "False alarm")

        assert resolved_alert.status == "resolved"
        assert resolved_alert.resolved_at is not None


class TestNotificationChannels:
    """Test suite for notification channels."""

    @pytest.mark.asyncio
    async def test_email_channel_send_success(self):
        """Test successful email notification."""
        from voc_app.notifications.email import EmailChannel

        channel = EmailChannel()

        with patch("voc_app.notifications.email.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            result = await channel.send(
                recipient="test@example.com",
                subject="Test Alert",
                message="This is a test alert",
                smtp_host="localhost",
                smtp_port=587,
            )

            assert result.success is True
            assert result.channel == "email"
            assert result.recipient == "test@example.com"
            mock_server.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_email_channel_send_failure(self):
        """Test email notification failure handling."""
        from voc_app.notifications.email import EmailChannel

        channel = EmailChannel()

        with patch("voc_app.notifications.email.smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = Exception("SMTP connection failed")

            result = await channel.send(
                recipient="test@example.com",
                subject="Test Alert",
                message="This is a test alert",
            )

            assert result.success is False
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_webhook_channel_send_success(self):
        """Test successful webhook notification."""
        from voc_app.notifications.webhook import WebhookChannel

        channel = WebhookChannel()

        with patch("voc_app.notifications.webhook.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

            result = await channel.send(
                recipient="https://example.com/webhook",
                subject="Test Alert",
                message="This is a test alert",
                severity="high",
            )

            assert result.success is True
            assert result.channel == "webhook"

    @pytest.mark.asyncio
    async def test_webhook_channel_http_error(self):
        """Test webhook notification HTTP error handling."""
        from voc_app.notifications.webhook import WebhookChannel
        import httpx

        channel = WebhookChannel()

        with patch("voc_app.notifications.webhook.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            
            mock_client.return_value.__aenter__.return_value.post.side_effect = httpx.HTTPStatusError(
                "Server error",
                request=MagicMock(),
                response=mock_response,
            )

            result = await channel.send(
                recipient="https://example.com/webhook",
                subject="Test Alert",
                message="This is a test alert",
            )

            assert result.success is False
            assert "500" in result.error


class TestAlertRuleMatching:
    """Test alert rule matching logic."""

    def test_sentiment_rule_match(self):
        """Test sentiment-based rule matching."""
        from voc_app.services.alert_service import AlertService

        service = AlertService(AsyncMock())

        insight = Insight(
            id=uuid.uuid4(),
            feedback_id=uuid.uuid4(),
            summary="Unhappy customer",
            sentiment_score=-0.7,
        )

        rule = AlertRule(
            id=uuid.uuid4(),
            name="Negative Sentiment",
            rule_type="sentiment_threshold",
            threshold_value=-0.5,
            enabled=True,
        )

        assert service._insight_matches_rule(insight, rule) is True

    def test_keyword_rule_match(self):
        """Test keyword-based rule matching."""
        from voc_app.services.alert_service import AlertService

        service = AlertService(AsyncMock())

        insight = Insight(
            id=uuid.uuid4(),
            feedback_id=uuid.uuid4(),
            summary="The application crashed unexpectedly",
        )

        rule = AlertRule(
            id=uuid.uuid4(),
            name="Crash Detection",
            rule_type="keyword",
            keywords={"terms": ["crash", "error"]},
            enabled=True,
        )

        assert service._insight_matches_rule(insight, rule) is True

    def test_competitor_mention_rule_match(self):
        """Test competitor mention rule matching."""
        from voc_app.services.alert_service import AlertService

        service = AlertService(AsyncMock())

        insight = Insight(
            id=uuid.uuid4(),
            feedback_id=uuid.uuid4(),
            summary="Considering switch",
            competitor_mentions=[{"competitor_name": "CompetitorX", "context": "comparison"}],
        )

        rule = AlertRule(
            id=uuid.uuid4(),
            name="Competitor Mentions",
            rule_type="competitor_mention",
            competitor_filters={"names": ["CompetitorX", "CompetitorY"]},
            enabled=True,
        )

        assert service._insight_matches_rule(insight, rule) is True
