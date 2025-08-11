"""Add user_id to story_revisions and backfill

Revision ID: 614efd9315c7
Revises: 36ec1463aed4
Create Date: 2025-08-10 16:58:06.253618

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '614efd9315c7'
down_revision: Union[str, None] = '36ec1463aed4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Add column as nullable first
    op.add_column(
        "story_revisions",
        sa.Column("user_id", sa.Integer(), nullable=True)
    )

    # Backfill from posts.user_id (Postgres-safe)
    op.execute("""
        UPDATE story_revisions sr
        SET user_id = p.user_id
        FROM posts p
        WHERE sr.post_id = p.id
          AND sr.user_id IS NULL
    """)

    # Add FK + index
    op.create_foreign_key(
        "fk_story_revisions_user_id_users",
        "story_revisions", "users",
        ["user_id"], ["id"],
        ondelete="CASCADE"
    )
    op.create_index(
        "ix_story_revisions_user_id",
        "story_revisions", ["user_id"]
    )

    # Enforce NOT NULL after backfill
    op.alter_column("story_revisions", "user_id", nullable=False)

def downgrade():
    op.drop_index("ix_story_revisions_user_id", table_name="story_revisions")
    op.drop_constraint("fk_story_revisions_user_id_users", "story_revisions", type_="foreignkey")
    op.drop_column("story_revisions", "user_id")