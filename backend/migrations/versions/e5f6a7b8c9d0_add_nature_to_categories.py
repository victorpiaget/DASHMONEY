"""add nature column to categories

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('categories') as batch_op:
        batch_op.add_column(
            sa.Column('nature', sa.String(16), nullable=True),
        )
        batch_op.create_check_constraint(
            'ck_categories_nature_values',
            "nature IS NULL OR nature IN ('NEED', 'WANT', 'SAVING')",
        )


def downgrade() -> None:
    with op.batch_alter_table('categories') as batch_op:
        batch_op.drop_constraint('ck_categories_nature_values', type_='check')
        batch_op.drop_column('nature')
