"""add trade_type column to trades

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-03-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3a4b5c6d7e8'
down_revision: Union[str, Sequence[str], None] = 'e2f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'trades',
        sa.Column('trade_type', sa.String(16), nullable=False, server_default='TRADE'),
    )
    # Backfill existing asset transfers based on label convention
    op.execute("""
        UPDATE trades
        SET trade_type = 'TRANSFER'
        WHERE (label LIKE 'Transfert vers %' OR label LIKE 'Transfert depuis %')
          AND linked_cash_tx_id IS NULL
    """)


def downgrade() -> None:
    op.drop_column('trades', 'trade_type')
