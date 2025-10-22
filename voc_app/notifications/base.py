"""Base notification channel interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class NotificationResult:
    """Result of a notification delivery attempt."""

    success: bool
    channel: str
    recipient: str
    error: str | None = None
    metadata: dict[str, Any] | None = None


class NotificationChannel(ABC):
    """Abstract base class for notification channels."""

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """Return the name of this notification channel."""

    @abstractmethod
    async def send(
        self,
        recipient: str,
        subject: str,
        message: str,
        **kwargs: Any,
    ) -> NotificationResult:
        """Send a notification through this channel."""
