"""add subscription_plans table

Revision ID: 012
Revises: 011
Create Date: 2026-02-23 17:47:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '012'
down_revision: Union[str, None] = '011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'subscription_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('price_cents', sa.Integer(), nullable=False),
        sa.Column('trial_days', sa.Integer(), nullable=False, server_default='14'),
        sa.Column('api_call_limit', sa.Integer(), nullable=True),
        sa.Column('lead_limit', sa.Integer(), nullable=True),
        sa.Column('appointment_limit', sa.Integer(), nullable=True),
        sa.Column('features', postgresql.JSONB(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index(op.f('ix_subscription_plans_id'), 'subscription_plans', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_subscription_plans_id'), table_name='subscription_plans')
    op.drop_table('subscription_plans')
