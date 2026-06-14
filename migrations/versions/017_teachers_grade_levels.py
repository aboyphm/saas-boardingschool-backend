"""teachers: add grade_levels JSON column

Revision ID: 017
Revises: 016
Create Date: 2026-06-07
"""
from __future__ import annotations
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "teachers",
        sa.Column("grade_levels", JSON, nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("teachers", "grade_levels")
