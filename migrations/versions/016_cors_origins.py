"""cors: add cors_origins table

Revision ID: 016
Revises: 015
Create Date: 2026-06-01
"""
from __future__ import annotations
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cors_origins",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("origin", sa.String(500), nullable=False, unique=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_cors_origins_origin", "cors_origins", ["origin"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_cors_origins_origin", table_name="cors_origins")
    op.drop_table("cors_origins")
