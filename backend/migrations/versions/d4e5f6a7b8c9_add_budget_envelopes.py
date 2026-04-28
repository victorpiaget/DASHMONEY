"""add budget_envelopes table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'budget_envelopes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('profile_id', sa.String(36), sa.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('category', sa.String(128), nullable=False),
        sa.Column('subcategory', sa.String(128), nullable=True),
        sa.Column('kind', sa.String(16), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('currency', sa.String(8), nullable=False),
    )
    op.execute("""
        CREATE UNIQUE INDEX uq_budget_envelopes_profile_cat_sub_kind
        ON budget_envelopes (profile_id, category, COALESCE(subcategory, ''), kind)
    """)


def downgrade() -> None:
    op.drop_index('uq_budget_envelopes_profile_cat_sub_kind', table_name='budget_envelopes')
    op.drop_table('budget_envelopes')
