"""Add leads table

Revision ID: 010_add_leads_table
Revises: 009_add_appointments_and_availability
Create Date: 2025-02-23 06:30:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '010_add_leads_table'
down_revision = '009_add_appointments_and_availability'
branch_labels = None
depends_on = None


def upgrade():
    # Create lead source and status enums
    lead_source_enum = postgresql.ENUM('call', 'web', 'manual', name='leadsource', create_type=False)
    lead_source_enum.create(op.get_bind(), checkfirst=True)
    
    lead_status_enum = postgresql.ENUM('new', 'contacted', 'converted', 'lost', name='leadstatus', create_type=False)
    lead_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Create leads table
    op.create_table(
        'leads',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('business_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('caller_name', sa.String(length=255), nullable=False),
        sa.Column('caller_phone', sa.String(length=50), nullable=False),
        sa.Column('caller_email', sa.String(length=255), nullable=True),
        sa.Column('service_needed', sa.String(length=500), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('source', lead_source_enum, nullable=False),
        sa.Column('status', lead_status_enum, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_leads_business_id'), 'leads', ['business_id'], unique=False)
    op.create_index(op.f('ix_leads_status'), 'leads', ['status'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_leads_status'), table_name='leads')
    op.drop_index(op.f('ix_leads_business_id'), table_name='leads')
    op.drop_table('leads')
    
    # Drop enums
    lead_status_enum = postgresql.ENUM('new', 'contacted', 'converted', 'lost', name='leadstatus')
    lead_status_enum.drop(op.get_bind(), checkfirst=True)
    
    lead_source_enum = postgresql.ENUM('call', 'web', 'manual', name='leadsource')
    lead_source_enum.drop(op.get_bind(), checkfirst=True)
