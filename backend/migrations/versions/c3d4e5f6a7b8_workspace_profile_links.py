"""add workspace_profile_links table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-19 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'workspace_profile_links',
        sa.Column('workspace_id', sa.String(36), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('profile_id', sa.String(36), sa.ForeignKey('profiles.id', ondelete='CASCADE'), primary_key=True),
    )
    # Migrate existing data: link each profile to its home workspace
    op.execute(
        "INSERT INTO workspace_profile_links (workspace_id, profile_id) "
        "SELECT workspace_id, id FROM profiles"
    )


def downgrade() -> None:
    op.drop_table('workspace_profile_links')
