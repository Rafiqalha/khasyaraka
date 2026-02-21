"""Add hearts column to users

Revision ID: a1b2c3d4e5f6
Revises: 2007d6db617f
Create Date: 2026-02-12 07:30:00.000000+07:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '2007d6db617f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add hearts column if it doesn't exist yet."""
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]
    if 'hearts' not in columns:
        op.add_column('users', sa.Column('hearts', sa.Integer(), nullable=False, server_default='5'))


def downgrade() -> None:
    """Remove hearts column."""
    op.drop_column('users', 'hearts')
