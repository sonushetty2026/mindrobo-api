"""add admin_audit_log table

Revision ID: 016
Revises: 015
Create Date: 2026-02-23 17:49:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '016'
down_revision: Union[str, None] = '015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'admin_audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('admin_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('target_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    
    # Add foreign keys
    op.create_foreign_key(
        'fk_admin_audit_log_admin_id',
        'admin_audit_log', 'users',
        ['admin_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_admin_audit_log_target_user_id',
        'admin_audit_log', 'users',
        ['target_user_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Add indexes
    op.create_index(op.f('ix_admin_audit_log_id'), 'admin_audit_log', ['id'], unique=False)
    op.create_index(op.f('ix_admin_audit_log_admin_id'), 'admin_audit_log', ['admin_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_admin_audit_log_admin_id'), table_name='admin_audit_log')
    op.drop_index(op.f('ix_admin_audit_log_id'), table_name='admin_audit_log')
    op.drop_constraint('fk_admin_audit_log_target_user_id', 'admin_audit_log', type_='foreignkey')
    op.drop_constraint('fk_admin_audit_log_admin_id', 'admin_audit_log', type_='foreignkey')
    op.drop_table('admin_audit_log')
