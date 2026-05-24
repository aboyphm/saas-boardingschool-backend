"""make employee_contracts and payroll_runs tenant_id nullable (platform-level support)

Revision ID: 005
Revises: 004
Create Date: 2026-05-17
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── employee_contracts.tenant_id → nullable ─────────────────────────────
    op.alter_column("employee_contracts", "tenant_id", nullable=True)

    # Add a platform-scoped uniqueness index (tenant_id IS NULL case).
    # The existing uq_active_contract_user_tenant skips NULLs because
    # NULL != NULL in SQL, so we need a separate partial index.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_active_contract_platform_user
        ON employee_contracts (user_id)
        WHERE status = 'active' AND tenant_id IS NULL
        """
    )

    # ─── payroll_runs.tenant_id → nullable ───────────────────────────────────
    op.alter_column("payroll_runs", "tenant_id", nullable=True)

    # Same pattern: existing uq_payroll_run_period_tenant skips NULLs.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_payroll_run_period_platform
        ON payroll_runs (period_month, period_year)
        WHERE status != 'cancelled' AND tenant_id IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_payroll_run_period_platform")
    op.alter_column("payroll_runs", "tenant_id", nullable=False)

    op.execute("DROP INDEX IF EXISTS uq_active_contract_platform_user")
    op.alter_column("employee_contracts", "tenant_id", nullable=False)
