"""Add `pending` to storystatus enum

Story creation now enqueues an async moderation task (UPGRADE_PLAN Phase 2).
Between story insert and moderation completion the row sits in a new
`pending` state so the public list hides it and the moderator queue can find it.

Postgres enum types are immutable-ish — `ALTER TYPE ... ADD VALUE` is the
supported dance. `IF NOT EXISTS` keeps this migration idempotent against dev
DBs that already got it via `Base.metadata.create_all` from tests.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-22 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # recommended by claude opus 4.7: ADD VALUE must run OUTSIDE a
    # transaction on Postgres <12. Alembic wraps migrations in a transaction
    # by default; the COMMIT + BEGIN dance forces autocommit for this one
    # statement then re-enters the transactional scope. On Postgres >=12
    # this is unnecessary but harmless.
    op.execute("COMMIT")
    op.execute("ALTER TYPE storystatus ADD VALUE IF NOT EXISTS 'pending'")
    op.execute("BEGIN")


def downgrade() -> None:
    # recommended by claude opus 4.7: Postgres has no `DROP VALUE` for enum
    # types. A proper downgrade requires: rename the type, create a new one
    # without `pending`, migrate every referencing column, drop the old.
    # Not worth the surface area for a rollback that will never happen
    # cleanly in production. Fail loudly instead.
    raise NotImplementedError(
        "Dropping an enum value in Postgres requires a full type rewrite; "
        "leave 'pending' in place or write a purpose-built migration."
    )
