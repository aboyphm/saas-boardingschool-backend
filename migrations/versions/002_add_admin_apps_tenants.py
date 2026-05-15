"""add admin_apps_tenants table

Revision ID: 002
Revises: 001
Create Date: 2026-05-15
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_apps_tenants",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "admin_apps_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "admin_apps_user_id",
            "tenant_id",
            name="uq_admin_apps_user_tenant",
        ),
    )
    op.create_index(
        "ix_admin_apps_tenants_admin_apps_user_id",
        "admin_apps_tenants",
        ["admin_apps_user_id"],
    )
    op.create_index(
        "ix_admin_apps_tenants_tenant_id",
        "admin_apps_tenants",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_admin_apps_tenants_tenant_id", table_name="admin_apps_tenants")
    op.drop_index(
        "ix_admin_apps_tenants_admin_apps_user_id", table_name="admin_apps_tenants"
    )
    op.drop_table("admin_apps_tenants")
