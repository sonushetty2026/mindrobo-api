"""Add email verification and password reset fields

Revision ID: 008_add_verification_fields
Revises: 007_add_onboarding_fields_to_business
Create Date: 2026-02-23 04:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008_add_verification_fields'
down_revision = '007_add_onboarding_fields_to_business'
branch_labels = None
depends_on = None


def upgrade():
    # Add email verification fields
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('verification_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('verification_expires', sa.DateTime(), nullable=True))
    
    # Add password reset fields
    op.add_column('users', sa.Column('reset_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('reset_expires', sa.DateTime(), nullable=True))
    
    # Add indexes for token lookups
    op.create_index('ix_users_verification_token', 'users', ['verification_token'])
    op.create_index('ix_users_reset_token', 'users', ['reset_token'])
    
    # Fix is_active type if needed (was String, should be Boolean)
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
