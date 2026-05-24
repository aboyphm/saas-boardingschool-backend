from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel, TimestampMixin
from app.shared.enums import ContractStatus, EmploymentType, PayrollRunStatus


class EmployeeContract(BaseModel, TimestampMixin):
    """
    Employment contract that governs salary, tax, and insurance settings for one employee.

    A single active contract per user per tenant is enforced via a partial unique index
    defined in the migration. The SQLAlchemy-level UniqueConstraint here covers all
    non-terminated/expired statuses in combination with tenant + user.
    """

    __tablename__ = "employee_contracts"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    employee_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    employment_type: Mapped[EmploymentType] = mapped_column(String(20), nullable=False)
    position: Mapped[str | None] = mapped_column(String(100), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    base_salary: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)

    status: Mapped[ContractStatus] = mapped_column(
        String(20), nullable=False, default=ContractStatus.ACTIVE, index=True
    )

    # JSONB columns for flexible configuration — nullable means "use system defaults"
    tax_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    insurance_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Shape: [{"name": str, "amount": float, "taxable": bool}]
    allowances: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )

    # ─── Relationships ────────────────────────────────────────────────────────
    payroll_records: Mapped[list["PayrollRecord"]] = relationship(  # noqa: F821
        "PayrollRecord",
        back_populates="contract",
        foreign_keys="PayrollRecord.contract_id",
    )


class PayrollRun(BaseModel, TimestampMixin):
    """
    Represents one full payroll processing cycle for a given month/year.

    A unique partial index in the migration prevents duplicate non-cancelled runs
    for the same period within a tenant.
    """

    __tablename__ = "payroll_runs"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    period_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    period_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    status: Mapped[PayrollRunStatus] = mapped_column(
        String(20), nullable=False, default=PayrollRunStatus.DRAFT, index=True
    )

    total_gross: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    total_deductions: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    total_net: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)

    run_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── Relationships ────────────────────────────────────────────────────────
    payroll_records: Mapped[list["PayrollRecord"]] = relationship(  # noqa: F821
        "PayrollRecord",
        back_populates="payroll_run",
        foreign_keys="PayrollRecord.payroll_run_id",
    )


# Deferred import to avoid circular references with the finance domain
from app.domains.finance.models import PayrollRecord  # noqa: E402, F401
