"""add school_type to tenants, clear religion server_default

Revision ID: 008
Revises: 007
Create Date: 2026-05-17
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("school_type", sa.String(20), nullable=False, server_default="boarding"),
    )
    op.alter_column(
        "students", "religion",
        existing_type=sa.String(50),
        existing_nullable=False,
        server_default="",
    )


def downgrade() -> None:
    op.drop_column("tenants", "school_type")
    op.alter_column(
        "students", "religion",
        existing_type=sa.String(50),
        existing_nullable=False,
        server_default="Islam",
    )
