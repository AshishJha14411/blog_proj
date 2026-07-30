"""Add full-text search to stories

Adds a GENERATED tsvector column over (title, content) plus a GIN index, so
`GET /stories/search?q=...` can do real Postgres full-text search — ranked,
stemmed, index-backed — instead of a `LIKE '%term%'` sequential scan.

- GENERATED ALWAYS ... STORED: Postgres keeps the tsvector in sync on every
  insert/update automatically; the app never has to populate it.
- weight A on title, B on content: a title match ranks above a body match.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-26 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE stories
        ADD COLUMN IF NOT EXISTS search_vector tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(content, '')), 'B')
        ) STORED
        """
    )
    # CREATE INDEX CONCURRENTLY can't run inside a transaction — it builds
    # without taking a write lock, so on a large `stories` table this avoids
    # blocking publishes for the duration of the build. `autocommit_block()`
    # commits the migration's transaction, runs this in autocommit, then
    # resumes — the Alembic-sanctioned way to issue non-transactional DDL.
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_stories_search_vector "
            "ON stories USING GIN (search_vector)"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_stories_search_vector")
    op.execute("ALTER TABLE stories DROP COLUMN IF EXISTS search_vector")
