"""add user trial and roles fields

Revision ID: 013
Revises: 012
Create Date: 2026-02-23 17:47:30.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '013'
down_revision: Union[str, None] = '012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to users table
    op.add_column('users', sa.Column('role', sa.String(), nullable=False, server_default='user'))
    op.add_column('users', sa.Column('is_trial', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('trial_ends_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('is_paused', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('paused_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('users', sa.Column('fcm_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(), nullable=True))
    
    # Add foreign key to subscription_plans
    op.create_foreign_key(
        'fk_users_plan_id',
        'users', 'subscription_plans',
        ['plan_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_users_plan_id', 'users', type_='foreignkey')
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'fcm_token')
    op.drop_column('users', 'plan_id')
    op.drop_column('users', 'paused_at')
    op.drop_column('users', 'is_paused')
    op.drop_column('users', 'trial_ends_at')
    op.drop_column('users', 'is_trial')
    op.drop_column('users', 'role')
