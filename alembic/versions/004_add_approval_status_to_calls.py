"""Add approval_status to calls table

Revision ID: 004
Revises: 003
Create Date: 2026-02-22
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the approval_status enum type
    op.execute("CREATE TYPE approval_status AS ENUM ('pending_approval', 'approved', 'rejected')")
    
    # Add the column with default value
    op.add_column(
        "calls",
        sa.Column("approval_status", sa.Enum("pending_approval", "approved", "rejected", name="approval_status"), 
                  server_default="pending_approval", nullable=False)
    )


def downgrade() -> None:
    op.drop_column("calls", "approval_status")
    op.execute("DROP TYPE IF EXISTS approval_status")
