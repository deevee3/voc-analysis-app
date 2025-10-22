"""Notification channel integrations for alerts."""

from .base import NotificationChannel, NotificationResult
from .email import EmailChannel
from .webhook import WebhookChannel

__all__ = ["NotificationChannel", "NotificationResult", "EmailChannel", "WebhookChannel"]
