"""Processed insight model."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID

from .base import Base


class Insight(Base):
    """Stores structured insight extracted from `Feedback`."""

    __tablename__ = "insights"
    __table_args__ = (
        Index("ix_insights_sentiment", "sentiment_label", "journey_stage"),
        Index("ix_insights_created_at", "created_at"),
        Index("ix_insights_sentiment_score", "sentiment_score"),
        Index("ix_insights_urgency", "urgency_level"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    feedback_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("feedback.id", ondelete="CASCADE"), nullable=False
    )
    sentiment_score: Mapped[float | None] = mapped_column(Numeric(precision=5, scale=2))
    sentiment_label: Mapped[str | None] = mapped_column(String(16))
    summary: Mapped[str | None] = mapped_column(Text)
    pain_points: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    feature_requests: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    competitor_mentions: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    customer_context: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    journey_stage: Mapped[str | None] = mapped_column(String(64))
    urgency_level: Mapped[int | None] = mapped_column()

    feedback: Mapped["Feedback"] = relationship(back_populates="insights")
    themes: Mapped[list["InsightThemeLink"]] = relationship(
        back_populates="insight", cascade="all, delete-orphan"
    )
    alert_events: Mapped[list["AlertEvent"]] = relationship(back_populates="primary_insight")
