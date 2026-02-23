"""Add leads table

Revision ID: 010_add_leads_table
Revises: 009_add_appointments_and_availability
Create Date: 2026-02-23 06:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010_add_leads_table'
down_revision = '009_add_appointments_and_availability'
branch_labels = None
depends_on = None


def upgrade():
    # Create lead_source enum
    lead_source_enum = postgresql.ENUM('call', 'web', name='lead_source')
    lead_source_enum.create(op.get_bind(), checkfirst=True)
    
    # Create lead_status enum
    lead_status_enum = postgresql.ENUM('new', 'contacted', 'converted', 'lost', name='lead_status')
    lead_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Create leads table
    op.create_table(
        'leads',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('business_id', sa.String(), nullable=False),
        sa.Column('caller_name', sa.String(), nullable=True),
        sa.Column('caller_phone', sa.String(), nullable=False),
        sa.Column('service_needed', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('source', lead_source_enum, nullable=False, server_default='call'),
        sa.Column('status', lead_status_enum, nullable=False, server_default='new'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_leads_business_id', 'leads', ['business_id'])
    op.create_index('ix_leads_status', 'leads', ['status'])
    op.create_index('ix_leads_created_at', 'leads', ['created_at'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_leads_created_at', table_name='leads')
    op.drop_index('ix_leads_status', table_name='leads')
    op.drop_index('ix_leads_business_id', table_name='leads')
    
    # Drop table
    op.drop_table('leads')
    
    # Drop enums
    lead_status_enum = postgresql.ENUM('new', 'contacted', 'converted', 'lost', name='lead_status')
    lead_status_enum.drop(op.get_bind(), checkfirst=True)
    
    lead_source_enum = postgresql.ENUM('call', 'web', name='lead_source')
    lead_source_enum.drop(op.get_bind(), checkfirst=True)
