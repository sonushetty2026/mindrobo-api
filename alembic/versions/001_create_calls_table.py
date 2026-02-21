"""Create calls table

Revision ID: 001
Revises: None
Create Date: 2026-02-21
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "calls",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("call_id", sa.String, unique=True, index=True, nullable=False),
        sa.Column("caller_phone", sa.String, nullable=True),
        sa.Column("business_id", sa.String, index=True, nullable=True),
        sa.Column("status", sa.Enum("active", "completed", "failed", name="call_status"), default="active"),
        sa.Column("outcome", sa.Enum("callback_scheduled", "lead_captured", "escalated", "voicemail", name="call_outcome"), nullable=True),
        sa.Column("transcript", sa.Text, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("lead_name", sa.String, nullable=True),
        sa.Column("lead_address", sa.String, nullable=True),
        sa.Column("service_type", sa.String, nullable=True),
        sa.Column("urgency", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("calls")
    op.execute("DROP TYPE IF EXISTS call_status")
    op.execute("DROP TYPE IF EXISTS call_outcome")
