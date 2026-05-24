"""add phone column to teachers

Revision ID: 007
Revises: 006
Create Date: 2026-05-17
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "teachers",
        sa.Column("phone", sa.String(30), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("teachers", "phone")
