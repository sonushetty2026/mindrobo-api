"""add approval_status to calls

Revision ID: 011
Revises: 010b
Create Date: 2026-02-22 12:24:54.831108
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '011'
down_revision: Union[str, None] = '010b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type first
    approval_status_enum = postgresql.ENUM('pending', 'approved', 'rejected', name='approval_status', create_type=True)
    approval_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Add column using the enum
    op.add_column('calls', sa.Column('approval_status', sa.Enum('pending', 'approved', 'rejected', name='approval_status'), nullable=True, server_default='pending'))
    
    # Index changes
    op.alter_column('calls', 'call_id',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.drop_constraint('calls_call_id_key', 'calls', type_='unique')
    op.drop_index('ix_calls_call_id', table_name='calls')
    op.create_index(op.f('ix_calls_call_id'), 'calls', ['call_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_calls_call_id'), table_name='calls')
    op.create_index('ix_calls_call_id', 'calls', ['call_id'], unique=False)
    op.create_unique_constraint('calls_call_id_key', 'calls', ['call_id'])
    op.alter_column('calls', 'call_id',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.drop_column('calls', 'approval_status')
    
    # Drop enum type
    approval_status_enum = postgresql.ENUM('pending', 'approved', 'rejected', name='approval_status')
    approval_status_enum.drop(op.get_bind(), checkfirst=True)
