"""add webhook retries table

Revision ID: 017
Revises: 016
Create Date: 2026-02-24 01:25:21.629681
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '017'
down_revision: Union[str, None] = '016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'webhook_retries',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('service', sa.String(), nullable=False),
        sa.Column('payload', JSONB(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_webhook_retries_service', 'webhook_retries', ['service'])
    op.create_index('ix_webhook_retries_status', 'webhook_retries', ['status'])
    op.create_index('ix_webhook_retries_created_at', 'webhook_retries', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_webhook_retries_created_at', 'webhook_retries')
    op.drop_index('ix_webhook_retries_status', 'webhook_retries')
    op.drop_index('ix_webhook_retries_service', 'webhook_retries')
    op.drop_table('webhook_retries')
