"""add employee_contracts, payroll_runs tables and extend payroll_records

Revision ID: 004
Revises: 003
Create Date: 2026-05-17
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── employee_contracts ───────────────────────────────────────────────────
    op.create_table(
        "employee_contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("employee_number", sa.String(50), nullable=True),
        sa.Column("employment_type", sa.String(20), nullable=False),
        sa.Column("position", sa.String(100), nullable=True),
        sa.Column("department", sa.String(100), nullable=True),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("base_salary", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("tax_config", postgresql.JSONB, nullable=True),
        sa.Column("insurance_config", postgresql.JSONB, nullable=True),
        sa.Column("allowances", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_employee_contracts_tenant_id", "employee_contracts", ["tenant_id"])
    op.create_index("ix_employee_contracts_user_id", "employee_contracts", ["user_id"])
    op.create_index("ix_employee_contracts_status", "employee_contracts", ["status"])

    # Partial unique index: one active contract per user per tenant
    op.execute(
        """
        CREATE UNIQUE INDEX uq_active_contract_user_tenant
        ON employee_contracts (tenant_id, user_id)
        WHERE status = 'active'
        """
    )

    # ─── payroll_runs ─────────────────────────────────────────────────────────
    op.create_table(
        "payroll_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period_month", sa.SmallInteger, nullable=False),
        sa.Column("period_year", sa.SmallInteger, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("total_gross", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("total_deductions", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("total_net", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column(
            "run_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=False,
        ),
        sa.Column(
            "approved_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_payroll_runs_tenant_id", "payroll_runs", ["tenant_id"])
    op.create_index("ix_payroll_runs_status", "payroll_runs", ["status"])

    # Partial unique index: one non-cancelled run per period per tenant
    op.execute(
        """
        CREATE UNIQUE INDEX uq_payroll_run_period_tenant
        ON payroll_runs (tenant_id, period_month, period_year)
        WHERE status != 'cancelled'
        """
    )

    # ─── payroll_records — extend with HR columns ─────────────────────────────
    op.add_column(
        "payroll_records",
        sa.Column(
            "contract_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("employee_contracts.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "payroll_records",
        sa.Column(
            "payroll_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("payroll_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "payroll_records",
        sa.Column("gross_salary", sa.Numeric(15, 2), nullable=True),
    )
    op.add_column(
        "payroll_records",
        sa.Column("tax_amount", sa.Numeric(15, 2), nullable=True),
    )
    op.add_column(
        "payroll_records",
        sa.Column("bpjs_employee", sa.Numeric(15, 2), nullable=True),
    )
    op.add_column(
        "payroll_records",
        sa.Column("bpjs_employer", sa.Numeric(15, 2), nullable=True),
    )
    op.add_column(
        "payroll_records",
        sa.Column(
            "other_deductions",
            sa.Numeric(15, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "payroll_records",
        sa.Column(
            "allowances_total",
            sa.Numeric(15, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "payroll_records",
        sa.Column(
            "one_time_adjustments",
            postgresql.JSONB,
            nullable=False,
            server_default="[]",
        ),
    )
    op.create_index("ix_payroll_records_contract_id", "payroll_records", ["contract_id"])
    op.create_index("ix_payroll_records_payroll_run_id", "payroll_records", ["payroll_run_id"])


def downgrade() -> None:
    # ─── payroll_records — remove HR columns ──────────────────────────────────
    op.drop_index("ix_payroll_records_payroll_run_id", "payroll_records")
    op.drop_index("ix_payroll_records_contract_id", "payroll_records")
    op.drop_column("payroll_records", "one_time_adjustments")
    op.drop_column("payroll_records", "allowances_total")
    op.drop_column("payroll_records", "other_deductions")
    op.drop_column("payroll_records", "bpjs_employer")
    op.drop_column("payroll_records", "bpjs_employee")
    op.drop_column("payroll_records", "tax_amount")
    op.drop_column("payroll_records", "gross_salary")
    op.drop_column("payroll_records", "payroll_run_id")
    op.drop_column("payroll_records", "contract_id")

    # ─── payroll_runs ─────────────────────────────────────────────────────────
    op.execute("DROP INDEX IF EXISTS uq_payroll_run_period_tenant")
    op.drop_index("ix_payroll_runs_status", "payroll_runs")
    op.drop_index("ix_payroll_runs_tenant_id", "payroll_runs")
    op.drop_table("payroll_runs")

    # ─── employee_contracts ───────────────────────────────────────────────────
    op.execute("DROP INDEX IF EXISTS uq_active_contract_user_tenant")
    op.drop_index("ix_employee_contracts_status", "employee_contracts")
    op.drop_index("ix_employee_contracts_user_id", "employee_contracts")
    op.drop_index("ix_employee_contracts_tenant_id", "employee_contracts")
    op.drop_table("employee_contracts")
