"""Add missing columns to story_revisions

Revision ID: 4c75c66d88f7
Revises: create_story_revisions
Create Date: 2025-08-10 16:42:32.179077

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c75c66d88f7'
down_revision: Union[str, None] = 'create_story_revisions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    # Add missing columns if they don't already exist
    op.add_column('story_revisions', sa.Column('prompt', sa.Text(), nullable=True))
    op.add_column('story_revisions', sa.Column('feedback', sa.Text(), nullable=True))
    op.add_column('story_revisions', sa.Column('model_name', sa.String(), nullable=True))
    op.add_column('story_revisions', sa.Column('provider_message_id', sa.String(), nullable=True))


def downgrade():
    op.drop_column('story_revisions', 'provider_message_id')
    op.drop_column('story_revisions', 'model_name')
    op.drop_column('story_revisions', 'feedback')
    op.drop_column('story_revisions', 'prompt')