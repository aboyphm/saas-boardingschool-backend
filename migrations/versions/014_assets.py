"""assets: add assets table

Revision ID: 014
Revises: 013
Create Date: 2026-05-30
"""
from __future__ import annotations
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(30), nullable=False, server_default="other"),
        sa.Column("serial_number", sa.String(100), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("condition", sa.String(20), nullable=False, server_default="good"),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("purchase_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("assets")
