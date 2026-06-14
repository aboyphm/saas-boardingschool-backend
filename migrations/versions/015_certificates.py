"""certificates: add certificates table

Revision ID: 015
Revises: 014
Create Date: 2026-05-30
"""
from __future__ import annotations
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "certificates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("student_id", UUID(as_uuid=True),
                  sa.ForeignKey("students.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("issued_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("certificate_number", sa.String(100), nullable=False, unique=True),
        sa.Column("certificate_type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("issued_at", sa.Date(), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("revocation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_certificates_certificate_number",
        "certificates", ["certificate_number"], unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_certificates_certificate_number", table_name="certificates")
    op.drop_table("certificates")
