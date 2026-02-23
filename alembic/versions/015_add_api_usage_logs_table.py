"""add api_usage_logs table

Revision ID: 015
Revises: 014
Create Date: 2026-02-23 17:48:30.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '015'
down_revision: Union[str, None] = '014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'api_usage_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('service', sa.String(), nullable=False),
        sa.Column('endpoint', sa.String(), nullable=False),
        sa.Column('cost_cents', sa.Integer(), nullable=False),
        sa.Column('request_data', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    
    # Add foreign key to users
    op.create_foreign_key(
        'fk_api_usage_logs_user_id',
        'api_usage_logs', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Add indexes
    op.create_index(op.f('ix_api_usage_logs_id'), 'api_usage_logs', ['id'], unique=False)
    op.create_index(op.f('ix_api_usage_logs_user_id'), 'api_usage_logs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_api_usage_logs_user_id'), table_name='api_usage_logs')
    op.drop_index(op.f('ix_api_usage_logs_id'), table_name='api_usage_logs')
    op.drop_constraint('fk_api_usage_logs_user_id', 'api_usage_logs', type_='foreignkey')
    op.drop_table('api_usage_logs')
