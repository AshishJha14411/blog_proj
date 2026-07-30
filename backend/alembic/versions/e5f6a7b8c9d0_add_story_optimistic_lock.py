"""Add optimistic-lock counter to stories

`row_version` backs SQLAlchemy's version_id_col optimistic locking so two
concurrent story edits can't silently clobber each other (lost update). Backfill
existing rows to 1 and make it NOT NULL.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-26 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stories",
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("stories", "row_version")
