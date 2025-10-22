"""Association table linking insights and themes."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID

from .base import Base


class InsightThemeLink(Base):
    """Many-to-many relationship between `Insight` and `Theme`."""

    __tablename__ = "insight_themes"
    __table_args__ = (UniqueConstraint("insight_id", "theme_id", name="uq_insight_theme"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    insight_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("insights.id", ondelete="CASCADE"), nullable=False
    )
    theme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("themes.id", ondelete="CASCADE"), nullable=False
    )
    weight: Mapped[float | None] = mapped_column(Numeric(precision=4, scale=2), nullable=True)

    insight: Mapped["Insight"] = relationship(back_populates="themes")
    theme: Mapped["Theme"] = relationship(back_populates="insight_links")
