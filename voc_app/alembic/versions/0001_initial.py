"""Initial database schema for Voice of Customer application.

Revision ID: 0001_initial
Revises: 
Create Date: 2025-10-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def _uuid_type():
    try:
        return sa.dialects.postgresql.UUID(as_uuid=True)
    except AttributeError:  # pragma: no cover
        return sa.String(length=36)


def _json_type():
    try:
        return sa.dialects.postgresql.JSONB()
    except AttributeError:  # pragma: no cover
        return sa.JSON()


def upgrade() -> None:
    uuid_type = _uuid_type()
    json_type = _json_type()

    op.create_table(
        "data_sources",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("name", sa.String(length=200), nullable=False, unique=True),
        sa.Column("platform", sa.String(length=100), nullable=False),
        sa.Column("config", json_type, nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("schedule", sa.String(length=100), nullable=True),
        sa.Column("last_crawl_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "crawl_runs",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("data_source_id", uuid_type, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("stats", json_type, nullable=True),
        sa.ForeignKeyConstraint(["data_source_id"], ["data_sources.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "feedback",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("data_source_id", uuid_type, nullable=False),
        sa.Column("crawl_run_id", uuid_type, nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("author_handle", sa.String(length=255), nullable=True),
        sa.Column("raw_content", sa.Text(), nullable=False),
        sa.Column("clean_content", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("metadata", json_type, nullable=True),
        sa.ForeignKeyConstraint(["data_source_id"], ["data_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["crawl_run_id"], ["crawl_runs.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_feedback_data_source_posted_at",
        "feedback",
        ["data_source_id", "posted_at"],
    )

    op.create_table(
        "themes",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("name", "is_system", name="uq_theme_name_scope"),
    )

    op.create_table(
        "alert_rules",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("name", sa.String(length=200), nullable=False, unique=True),
        sa.Column("rule_type", sa.String(length=50), nullable=False),
        sa.Column("threshold_value", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("keywords", json_type, nullable=True),
        sa.Column("competitor_filters", json_type, nullable=True),
        sa.Column("channels", json_type, nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "insights",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("feedback_id", uuid_type, nullable=False),
        sa.Column("sentiment_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("sentiment_label", sa.String(length=16), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("pain_points", json_type, nullable=True),
        sa.Column("feature_requests", json_type, nullable=True),
        sa.Column("competitor_mentions", json_type, nullable=True),
        sa.Column("customer_context", json_type, nullable=True),
        sa.Column("journey_stage", sa.String(length=64), nullable=True),
        sa.Column("urgency_level", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["feedback_id"], ["feedback.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_insights_sentiment",
        "insights",
        ["sentiment_label", "journey_stage"],
    )

    op.create_table(
        "alert_events",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("alert_rule_id", uuid_type, nullable=False),
        sa.Column("primary_insight_id", uuid_type, nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("payload", json_type, nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["alert_rule_id"], ["alert_rules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["primary_insight_id"], ["insights.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "insight_themes",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("insight_id", uuid_type, nullable=False),
        sa.Column("theme_id", uuid_type, nullable=False),
        sa.Column("weight", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.ForeignKeyConstraint(["insight_id"], ["insights.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["theme_id"], ["themes.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("insight_id", "theme_id", name="uq_insight_theme"),
    )


def downgrade() -> None:
    op.drop_table("insight_themes")
    op.drop_table("alert_events")
    op.drop_index("ix_insights_sentiment", table_name="insights")
    op.drop_table("insights")
    op.drop_table("alert_rules")
    op.drop_table("themes")
    op.drop_index("ix_feedback_data_source_posted_at", table_name="feedback")
    op.drop_table("feedback")
    op.drop_table("crawl_runs")
    op.drop_table("data_sources")
# End of script
