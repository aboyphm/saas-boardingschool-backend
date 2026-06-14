"""dormitory: partial unique index — one active room per student per tenant

Revision ID: 011
Revises: 010
Create Date: 2026-05-29
"""
from __future__ import annotations
from typing import Sequence, Union
from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_dormitory_assignment_active_student",
        "dormitory_assignments",
        ["tenant_id", "student_id"],
        unique=True,
        postgresql_where="is_active = true",
    )


def downgrade() -> None:
    op.drop_index("uq_dormitory_assignment_active_student", table_name="dormitory_assignments")
