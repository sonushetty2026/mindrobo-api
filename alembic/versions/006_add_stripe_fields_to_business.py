"""Add Stripe fields to businesses table

Revision ID: 006
Revises: 005
Create Date: 2026-02-22
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("businesses", sa.Column("stripe_customer_id", sa.String, unique=True, nullable=True))
    op.add_column("businesses", sa.Column("subscription_status", sa.String, server_default="trial", nullable=False))


def downgrade() -> None:
    op.drop_column("businesses", "subscription_status")
    op.drop_column("businesses", "stripe_customer_id")
