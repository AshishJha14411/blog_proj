"""added user_id to story revision

Revision ID: 36ec1463aed4
Revises: 4c75c66d88f7
Create Date: 2025-08-10 16:48:55.835962

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '36ec1463aed4'
down_revision: Union[str, None] = '4c75c66d88f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    op.drop_column("story_revisions", "user_id")

def downgrade():
    op.add_column("story_revisions", sa.Column("user_id", sa.Integer(), nullable=False))