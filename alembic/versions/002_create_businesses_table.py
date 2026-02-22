"""Create businesses table

Revision ID: 002
Revises: 001
Create Date: 2026-02-21
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "businesses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("owner_name", sa.String, nullable=True),
        sa.Column("owner_phone", sa.String, nullable=False),
        sa.Column("owner_email", sa.String, nullable=True),
        sa.Column("retell_agent_id", sa.String, unique=True, index=True, nullable=True),
        sa.Column("twilio_phone_number", sa.String, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("businesses")
