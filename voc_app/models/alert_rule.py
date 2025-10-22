"""Alert rule model."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, JSON, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID

from .base import Base


class AlertRule(Base):
    """Defines thresholds and conditions for triggering alerts."""

    __tablename__ = "alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    threshold_value: Mapped[float | None] = mapped_column(Numeric(precision=10, scale=2))
    keywords: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    competitor_filters: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    channels: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    alert_events: Mapped[list["AlertEvent"]] = relationship(
        back_populates="alert_rule", cascade="all, delete-orphan"
    )
