"""Webhook notification channel."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .base import NotificationChannel, NotificationResult

logger = logging.getLogger(__name__)


class WebhookChannel(NotificationChannel):
    """Send notifications via HTTP webhook."""

    @property
    def channel_name(self) -> str:
        return "webhook"

    async def send(
        self,
        recipient: str,  # webhook URL
        subject: str,
        message: str,
        **kwargs: Any,
    ) -> NotificationResult:
        """Send a webhook notification."""
        try:
            # Build payload
            payload = {
                "subject": subject,
                "message": message,
                "severity": kwargs.get("severity"),
                "alert_id": kwargs.get("alert_id"),
                "alert_rule": kwargs.get("alert_rule"),
                "insight_count": kwargs.get("insight_count", 0),
                "timestamp": kwargs.get("timestamp"),
            }

            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}

            # Get webhook configuration
            method = kwargs.get("method", "POST").upper()
            headers = kwargs.get("headers", {"Content-Type": "application/json"})
            timeout = kwargs.get("timeout", 30.0)

            async with httpx.AsyncClient() as client:
                if method == "POST":
                    response = await client.post(
                        recipient,
                        json=payload,
                        headers=headers,
                        timeout=timeout,
                    )
                elif method == "PUT":
                    response = await client.put(
                        recipient,
                        json=payload,
                        headers=headers,
                        timeout=timeout,
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()

            logger.info(f"Webhook sent to {recipient}: {subject} (status: {response.status_code})")

            return NotificationResult(
                success=True,
                channel=self.channel_name,
                recipient=recipient,
                metadata={
                    "status_code": response.status_code,
                    "subject": subject,
                },
            )

        except httpx.HTTPStatusError as exc:
            logger.error(
                f"Webhook notification failed to {recipient}: "
                f"HTTP {exc.response.status_code}"
            )
            return NotificationResult(
                success=False,
                channel=self.channel_name,
                recipient=recipient,
                error=f"HTTP {exc.response.status_code}: {exc.response.text}",
            )

        except Exception as exc:
            logger.exception(f"Webhook notification failed to {recipient}: {exc}")
            return NotificationResult(
                success=False,
                channel=self.channel_name,
                recipient=recipient,
                error=str(exc),
            )


class SlackWebhook(WebhookChannel):
    """Slack-specific webhook formatter."""

    @property
    def channel_name(self) -> str:
        return "slack"

    async def send(
        self,
        recipient: str,
        subject: str,
        message: str,
        **kwargs: Any,
    ) -> NotificationResult:
        """Send a Slack-formatted webhook notification."""
        severity = kwargs.get("severity", "medium")
        alert_url = kwargs.get("alert_url", "")

        # Slack color codes
        severity_colors = {
            "critical": "danger",
            "high": "warning",
            "medium": "#ffc107",
            "low": "good",
        }
        color = severity_colors.get(severity, "#808080")

        # Build Slack-specific payload
        slack_payload = {
            "attachments": [
                {
                    "color": color,
                    "title": subject,
                    "text": message,
                    "fields": [
                        {
                            "title": "Severity",
                            "value": severity.upper(),
                            "short": True,
                        },
                        {
                            "title": "Insights",
                            "value": str(kwargs.get("insight_count", 0)),
                            "short": True,
                        },
                    ],
                    "actions": [
                        {
                            "type": "button",
                            "text": "View Alert",
                            "url": alert_url,
                        }
                    ] if alert_url else [],
                    "footer": "VoC Alert System",
                    "ts": kwargs.get("timestamp"),
                }
            ]
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    recipient,
                    json=slack_payload,
                    timeout=30.0,
                )
                response.raise_for_status()

            logger.info(f"Slack notification sent: {subject}")

            return NotificationResult(
                success=True,
                channel=self.channel_name,
                recipient=recipient,
                metadata={"subject": subject},
            )

        except Exception as exc:
            logger.exception(f"Slack notification failed: {exc}")
            return NotificationResult(
                success=False,
                channel=self.channel_name,
                recipient=recipient,
                error=str(exc),
            )
