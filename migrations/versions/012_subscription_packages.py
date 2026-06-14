"""subscriptions: add subscription_packages table

Revision ID: 012
Revises: 011
Create Date: 2026-05-30
"""
from __future__ import annotations
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subscription_packages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("plan", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("price_monthly", sa.Float(), nullable=False, server_default="0"),
        sa.Column("price_yearly", sa.Float(), nullable=False, server_default="0"),
        sa.Column("feature_flags", JSON, nullable=False, server_default="[]"),
        sa.Column("quota_students", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quota_teachers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quota_storage_gb", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("subscription_packages")
