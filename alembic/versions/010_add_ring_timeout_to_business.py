"""Add ring_timeout_seconds to business

Revision ID: 010
Revises: 009
Create Date: 2026-02-23
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    # Add ring timeout setting for call forwarding (Issue #62)
    op.add_column('businesses', sa.Column('ring_timeout_seconds', sa.String(), nullable=True, server_default='20'))


def downgrade():
    op.drop_column('businesses', 'ring_timeout_seconds')
