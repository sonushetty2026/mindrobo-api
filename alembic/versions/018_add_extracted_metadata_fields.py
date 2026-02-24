"""Add extracted metadata fields to business table

Revision ID: 018_add_extracted_metadata_fields
Revises: 016_add_admin_audit_log_table
Create Date: 2026-02-24 18:08:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '018_add_extracted_metadata_fields'
down_revision = '016_add_admin_audit_log_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add extracted metadata fields to business table."""
    op.add_column('businesses', sa.Column('extracted_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('businesses', sa.Column('extraction_source_url', sa.String(), nullable=True))
    op.add_column('businesses', sa.Column('extracted_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove extracted metadata fields from business table."""
    op.drop_column('businesses', 'extracted_at')
    op.drop_column('businesses', 'extraction_source_url')
    op.drop_column('businesses', 'extracted_metadata')