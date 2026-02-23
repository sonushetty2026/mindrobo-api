"""add recording urls to calls

Revision ID: 006b
Revises: 006
Create Date: 2026-02-22 12:55:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '006b'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make idempotent - check if columns exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('calls')]
    
    if 'recording_url' not in columns:
        op.add_column('calls', sa.Column('recording_url', sa.String(), nullable=True))
    if 'transcript_url' not in columns:
        op.add_column('calls', sa.Column('transcript_url', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('calls', 'transcript_url')
    op.drop_column('calls', 'recording_url')
