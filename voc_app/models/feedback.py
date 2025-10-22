"""Customer feedback content model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID

from .base import Base


class Feedback(Base):
    """Stores raw and cleaned customer feedback entries."""

    __tablename__ = "feedback"
    __table_args__ = (
        Index("ix_feedback_data_source_posted_at", "data_source_id", "posted_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    data_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False
    )
    crawl_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crawl_runs.id", ondelete="SET NULL"), nullable=True
    )
    external_id: Mapped[str | None] = mapped_column(String(255))
    author_handle: Mapped[str | None] = mapped_column(String(255))
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    clean_content: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(10))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    url: Mapped[str | None] = mapped_column(String(500))
    extra_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSON().with_variant(JSONB, "postgresql"), nullable=True
    )

    data_source: Mapped["DataSource"] = relationship(back_populates="feedback_items")
    crawl_run: Mapped[Optional["CrawlRun"]] = relationship(back_populates="feedback_items")
    insights: Mapped[list["Insight"]] = relationship(
        back_populates="feedback", cascade="all, delete-orphan"
    )
