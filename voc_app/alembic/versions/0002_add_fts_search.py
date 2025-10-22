"""Add FTS5 virtual table for insight search.

Revision ID: 0002
Revises: 0001
Create Date: 2025-10-22 15:25:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create FTS5 virtual table for insights."""
    # Create FTS5 virtual table for full-text search on insights
    op.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS insights_fts USING fts5(
            insight_id UNINDEXED,
            summary,
            content='insights',
            content_rowid='rowid',
            tokenize='porter unicode61'
        )
    """)
    
    # Create triggers to keep FTS table in sync with insights table
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS insights_fts_insert AFTER INSERT ON insights
        BEGIN
            INSERT INTO insights_fts(rowid, insight_id, summary)
            VALUES (new.rowid, new.id, new.summary);
        END
    """)
    
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS insights_fts_update AFTER UPDATE ON insights
        BEGIN
            UPDATE insights_fts SET summary = new.summary
            WHERE rowid = old.rowid;
        END
    """)
    
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS insights_fts_delete AFTER DELETE ON insights
        BEGIN
            DELETE FROM insights_fts WHERE rowid = old.rowid;
        END
    """)
    
    # Populate FTS table with existing data
    op.execute("""
        INSERT INTO insights_fts(rowid, insight_id, summary)
        SELECT rowid, id, summary FROM insights WHERE summary IS NOT NULL
    """)


def downgrade() -> None:
    """Drop FTS5 virtual table and triggers."""
    op.execute("DROP TRIGGER IF EXISTS insights_fts_delete")
    op.execute("DROP TRIGGER IF EXISTS insights_fts_update")
    op.execute("DROP TRIGGER IF EXISTS insights_fts_insert")
    op.execute("DROP TABLE IF EXISTS insights_fts")
