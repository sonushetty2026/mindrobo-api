"""add onboarding fields to business

Revision ID: 007
Revises: 006
Create Date: 2026-02-22 22:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('businesses', sa.Column('industry', sa.String(), nullable=True))
    op.add_column('businesses', sa.Column('hours_of_operation', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('businesses', sa.Column('greeting_script', sa.Text(), nullable=True))
    op.add_column('businesses', sa.Column('faqs', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('businesses', 'faqs')
    op.drop_column('businesses', 'greeting_script')
    op.drop_column('businesses', 'hours_of_operation')
    op.drop_column('businesses', 'industry')
