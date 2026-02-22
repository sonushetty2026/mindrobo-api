"""add stripe fields to business

Revision ID: 005
Revises: 003
Create Date: 2026-02-22 12:45:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create subscription_status enum
    subscription_status_enum = postgresql.ENUM(
        'active', 'inactive', 'trialing', 'past_due', 'canceled',
        name='subscription_status',
        create_type=True
    )
    subscription_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Add Stripe fields to businesses table
    op.add_column('businesses', sa.Column('stripe_customer_id', sa.String(), nullable=True))
    op.add_column(
        'businesses',
        sa.Column(
            'subscription_status',
            sa.Enum('active', 'inactive', 'trialing', 'past_due', 'canceled', name='subscription_status'),
            server_default='inactive',
            nullable=True
        )
    )


def downgrade() -> None:
    op.drop_column('businesses', 'subscription_status')
    op.drop_column('businesses', 'stripe_customer_id')
    
    # Drop enum type
    subscription_status_enum = postgresql.ENUM(
        'active', 'inactive', 'trialing', 'past_due', 'canceled',
        name='subscription_status'
    )
    subscription_status_enum.drop(op.get_bind(), checkfirst=True)
