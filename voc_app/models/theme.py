"""Theme model representing reusable taxonomies for insights."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID

from .base import Base


class Theme(Base):
    """Represents a thematic bucket for grouping insights."""

    __tablename__ = "themes"
    __table_args__ = (UniqueConstraint("name", "is_system", name="uq_theme_name_scope"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    insight_links: Mapped[list["InsightThemeLink"]] = relationship(
        back_populates="theme", cascade="all, delete-orphan"
    )
