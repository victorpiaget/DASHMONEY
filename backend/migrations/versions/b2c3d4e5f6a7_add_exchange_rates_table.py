"""add exchange_rates table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'exchange_rates',
        sa.Column('currency', sa.String(8), primary_key=True),
        sa.Column('rate', sa.Numeric(24, 12), nullable=False),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Seed EUR = 1.0
    op.execute("INSERT INTO exchange_rates (currency, rate) VALUES ('EUR', 1.0)")


def downgrade() -> None:
    op.drop_table('exchange_rates')
