"""Add onboarding_step and onboarding_completed_at to businesses

Revision ID: 023e2600df05
Revises: 8b72b93f7e42
Create Date: 2026-02-24
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '023e2600df05'
down_revision: str = '017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('businesses', sa.Column('onboarding_step', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('businesses', sa.Column('onboarding_completed_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('businesses', 'onboarding_completed_at')
    op.drop_column('businesses', 'onboarding_step')
