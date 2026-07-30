"""Add webhook_endpoints table

Outbound webhooks (Phase 2c): a user registers a URL + gets a signing secret;
subscribed events (e.g. story.published) are HMAC-signed and POSTed to it by a
Celery task with retries. `event_types` is a JSONB array (empty = all events).

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-26 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "webhook_endpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("secret", sa.String(), nullable=False),
        sa.Column("event_types", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("disabled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_webhook_endpoints_user_id", "webhook_endpoints", ["user_id"],
        unique=False, if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_endpoints_user_id", table_name="webhook_endpoints", if_exists=True)
    op.drop_table("webhook_endpoints", if_exists=True)
