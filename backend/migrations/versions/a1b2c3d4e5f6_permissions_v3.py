"""rename profile_access permissions and add READ_ONLY workspace role

Revision ID: a1b2c3d4e5f6
Revises: f3a4b5c6d7e8
Create Date: 2026-03-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f3a4b5c6d7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename profile_access permissions: OWNER→ADMIN, MEMBER→WRITE
    op.execute("UPDATE profile_access SET permission='ADMIN' WHERE permission='OWNER'")
    op.execute("UPDATE profile_access SET permission='WRITE' WHERE permission='MEMBER'")


def downgrade() -> None:
    op.execute("UPDATE profile_access SET permission='OWNER' WHERE permission='ADMIN'")
    op.execute("UPDATE profile_access SET permission='MEMBER' WHERE permission='WRITE'")
    op.execute("UPDATE profile_access SET permission='MEMBER' WHERE permission='READ'")
