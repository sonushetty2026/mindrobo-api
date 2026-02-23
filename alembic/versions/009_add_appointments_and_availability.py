"""add appointments and availability fields

Revision ID: 009
Revises: 008
Create Date: 2026-02-23 05:55:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '009'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add availability fields to businesses table
    op.add_column('businesses', sa.Column('working_days', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('businesses', sa.Column('working_hours_start', sa.String(), nullable=True))
    op.add_column('businesses', sa.Column('working_hours_end', sa.String(), nullable=True))
    op.add_column('businesses', sa.Column('appointment_duration_minutes', sa.Integer(), nullable=True, server_default='60'))
    op.add_column('businesses', sa.Column('break_start', sa.String(), nullable=True))
    op.add_column('businesses', sa.Column('break_end', sa.String(), nullable=True))
    op.add_column('businesses', sa.Column('timezone', sa.String(), nullable=True))
    op.add_column('businesses', sa.Column('notifications_enabled', sa.Boolean(), nullable=True, server_default='true'))
    
    # Create appointments table
    op.create_table(
        'appointments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('customer_name', sa.String(), nullable=False),
        sa.Column('customer_phone', sa.String(), nullable=False),
        sa.Column('customer_email', sa.String(), nullable=True),
        sa.Column('service_needed', sa.String(), nullable=False),
        sa.Column('appointment_date', sa.Date(), nullable=False, index=True),
        sa.Column('appointment_time', sa.Time(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('confirmed', 'cancelled', 'completed', name='appointmentstatus'), nullable=False, index=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('appointments')
    op.execute('DROP TYPE appointmentstatus')
    
    op.drop_column('businesses', 'notifications_enabled')
    op.drop_column('businesses', 'timezone')
    op.drop_column('businesses', 'break_end')
    op.drop_column('businesses', 'break_start')
    op.drop_column('businesses', 'appointment_duration_minutes')
    op.drop_column('businesses', 'working_hours_end')
    op.drop_column('businesses', 'working_hours_start')
    op.drop_column('businesses', 'working_days')
