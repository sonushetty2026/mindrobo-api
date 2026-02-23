"""Add email verification and password reset fields

Revision ID: 008
Revises: 007b
Create Date: 2026-02-23 04:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007b'
branch_labels = None
depends_on = None


def upgrade():
    # Make idempotent - check if columns and indexes exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]
    indexes = [idx['name'] for idx in inspector.get_indexes('users')]
    
    # Add email verification fields
    if 'is_verified' not in columns:
        op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'))
    if 'verification_token' not in columns:
        op.add_column('users', sa.Column('verification_token', sa.String(), nullable=True))
    if 'verification_expires' not in columns:
        op.add_column('users', sa.Column('verification_expires', sa.DateTime(), nullable=True))
    
    # Add password reset fields
    if 'reset_token' not in columns:
        op.add_column('users', sa.Column('reset_token', sa.String(), nullable=True))
    if 'reset_expires' not in columns:
        op.add_column('users', sa.Column('reset_expires', sa.DateTime(), nullable=True))
    
    # Add indexes for token lookups
    if 'ix_users_verification_token' not in indexes:
        op.create_index('ix_users_verification_token', 'users', ['verification_token'])
    if 'ix_users_reset_token' not in indexes:
        op.create_index('ix_users_reset_token', 'users', ['reset_token'])
    
    # Fix is_active type if needed (was String, should be Boolean)
    # Check current type first
    is_active_col = next((col for col in inspector.get_columns('users') if col['name'] == 'is_active'), None)
    if is_active_col and str(is_active_col['type']) != 'BOOLEAN':
        op.alter_column('users', 'is_active',
                        existing_type=sa.String(),
                        type_=sa.Boolean(),
                        postgresql_using='is_active::boolean',
                        nullable=False,
                        server_default='true')


def downgrade():
    op.drop_index('ix_users_reset_token', 'users')
    op.drop_index('ix_users_verification_token', 'users')
    op.drop_column('users', 'reset_expires')
    op.drop_column('users', 'reset_token')
    op.drop_column('users', 'verification_expires')
    op.drop_column('users', 'verification_token')
    op.drop_column('users', 'is_verified')
    
    # Revert is_active type
    op.alter_column('users', 'is_active',
                    existing_type=sa.Boolean(),
                    type_=sa.String(),
                    nullable=False)
