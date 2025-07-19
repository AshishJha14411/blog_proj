"""seed roles

Revision ID: d78b3aeb43ed
Revises: 2e8af2bc2d41
Create Date: 2025-06-17 02:47:52.208715

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd78b3aeb43ed'
down_revision: Union[str, None] = '2e8af2bc2d41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    roles = sa.table(
        'roles',
        sa.column('id', sa.Integer),
        sa.column('name', sa.String),
        sa.column('description', sa.String),
    )
    op.bulk_insert(roles, [
        {'id': 1, 'name': 'user',       'description': 'Regular user'},
        {'id': 2, 'name': 'moderator',  'description': 'Content moderator'},
        {'id': 3, 'name': 'creator',    'description': 'Content creator'},
        {'id': 4, 'name': 'superadmin','description': 'Full system admin'},
    ])

def downgrade():
    op.execute("DELETE FROM roles WHERE id IN (1,2,3,4)")