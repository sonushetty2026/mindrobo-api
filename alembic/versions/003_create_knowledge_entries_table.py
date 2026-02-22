"""Create knowledge_entries table

Revision ID: 003
Revises: 002
Create Date: 2026-02-21
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("business_id", UUID(as_uuid=True), sa.ForeignKey("businesses.id"), index=True, nullable=False),
        sa.Column("source_url", sa.String, nullable=False),
        sa.Column("title", sa.String, nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("content_type", sa.String, server_default="webpage"),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("knowledge_entries")
