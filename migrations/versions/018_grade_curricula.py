"""academics: add grade_curricula table

Revision ID: 018
Revises: 017
Create Date: 2026-06-08
"""
from __future__ import annotations
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "grade_curricula",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("subject_id", UUID(as_uuid=True), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("grade_level", sa.String(10), nullable=False),
        sa.Column("is_lead", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "subject_id", "grade_level", name="uq_grade_curriculum"),
    )


def downgrade() -> None:
    op.drop_table("grade_curricula")
