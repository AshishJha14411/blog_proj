"""Seed automod user and AI Flagger role

Revision ID: 655d1dfe1126
Revises: 2b716709d6dd
Create Date: 2025-10-12 07:17:39.592168

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from passlib.context import CryptContext

# revision identifiers, used by Alembic.
revision: str = '655d1dfe1126'
down_revision: Union[str, None] = '2b716709d6dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    roles_table = sa.table(
        'roles',
        sa.column('id', sa.UUID),
        sa.column('name', sa.String),
        sa.column('description', sa.String)
    )
    users_table = sa.table(
        'users',
        sa.column('id', sa.UUID),
        sa.column('email', sa.String),
        sa.column('username', sa.String),
        sa.column('password_hash', sa.String),
        sa.column('role_id', sa.UUID),
        sa.column('is_verified', sa.Boolean)
    )

    # --- Step 2: Seed the new "AI Flagger" role ---
    

    # --- Step 3: Seed the new "automod" user ---
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    automod_password_hash = pwd_context.hash(str(uuid.uuid4()))

    op.bulk_insert(users_table, [
        {
            'id': str(uuid.uuid4()),
            'email': 'automod@system.local',
            'username': 'automod',
            'password_hash': automod_password_hash,
            'role_id': "efc422f1-dc73-46f4-9464-c9208461621d",
            'is_verified': True
        }
    ])


def downgrade() -> None:
    op.execute("DELETE FROM users WHERE username = 'automod'")