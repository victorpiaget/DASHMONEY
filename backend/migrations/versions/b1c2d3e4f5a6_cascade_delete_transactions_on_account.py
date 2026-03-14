"""cascade delete transactions when account is deleted

Revision ID: b1c2d3e4f5a6
Revises: a3f1c8e20b91
Create Date: 2026-03-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'a3f1c8e20b91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("fk_transactions_account_id_accounts", "transactions", type_="foreignkey")
    op.create_foreign_key(
        "fk_transactions_account_id_accounts",
        "transactions",
        "accounts",
        ["account_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_transactions_account_id_accounts", "transactions", type_="foreignkey")
    op.create_foreign_key(
        "fk_transactions_account_id_accounts",
        "transactions",
        "accounts",
        ["account_id"],
        ["id"],
        ondelete="RESTRICT",
    )
