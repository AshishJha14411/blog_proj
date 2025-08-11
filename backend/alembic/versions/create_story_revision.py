"""Create story_revisions table

Revision ID: create_story_revisions
Revises: 493f139329ad
Create Date: 2025-08-10 17:05:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = 'create_story_revisions'
down_revision: Union[str, None] = '493f139329ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'story_revisions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('post_id', sa.Integer(), sa.ForeignKey('posts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('notes', sa.Text(), nullable=True),  # feedback / change notes
    )
    op.create_index('ix_story_revisions_post_id', 'story_revisions', ['post_id'])
    op.create_index('ix_story_revisions_user_id', 'story_revisions', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_story_revisions_post_id', table_name='story_revisions')
    op.drop_index('ix_story_revisions_user_id', table_name='story_revisions')
    op.drop_table('story_revisions')
