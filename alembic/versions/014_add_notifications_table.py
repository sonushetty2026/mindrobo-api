"""add notifications table

Revision ID: 014
Revises: 013
Create Date: 2026-02-23 17:48:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '014'
down_revision: Union[str, None] = '013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum for notification type
    notification_type_enum = postgresql.ENUM(
        'system', 'admin', 'trial', 'billing',
        name='notification_type',
        create_type=True
    )
    notification_type_enum.create(op.get_bind(), checkfirst=True)
    
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('type', sa.Enum('system', 'admin', 'trial', 'billing', name='notification_type'), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    
    # Add foreign key to users
    op.create_foreign_key(
        'fk_notifications_user_id',
        'notifications', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Add indexes
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_id'), table_name='notifications')
    op.drop_constraint('fk_notifications_user_id', 'notifications', type_='foreignkey')
    op.drop_table('notifications')
    
    # Drop enum type
    notification_type_enum = postgresql.ENUM(
        'system', 'admin', 'trial', 'billing',
        name='notification_type'
    )
    notification_type_enum.drop(op.get_bind(), checkfirst=True)
