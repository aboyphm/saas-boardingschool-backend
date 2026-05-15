from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel, TimestampMixin
from app.shared.enums import BillingCycle, InvoiceStatus, PayrollStatus


class FeeCategory(BaseModel, TimestampMixin):
    """Configures standard fee types (e.g., tuition, dormitory, activity fee)."""

    __tablename__ = "fee_categories"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    is_recurring: Mapped[bool] = mapped_column(default=False, nullable=False)
    billing_cycle: Mapped[BillingCycle] = mapped_column(
        String(20), nullable=False, default=BillingCycle.MONTHLY
    )


class Invoice(BaseModel, TimestampMixin):
    """Financial invoice issued to a student/parent."""

    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("tenant_id", "invoice_number", name="uq_invoice_number_tenant"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    subtotal: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    discount: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    tax_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    tax_amount: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)

    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[InvoiceStatus] = mapped_column(
        String(20), nullable=False, default=InvoiceStatus.DRAFT, index=True
    )

    payment_gateway: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Serialised list of line items: [{"name": ..., "qty": ..., "price": ...}]
    items: Mapped[list] = mapped_column(JSON, default=list)

    # ─── Relationships ────────────────────────────────────────────────────────
    payments: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="invoice", cascade="all, delete-orphan"
    )


class Payment(BaseModel, TimestampMixin):
    """Records an individual payment against an invoice."""

    __tablename__ = "payments"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)
    payment_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gateway_response: Mapped[dict] = mapped_column(JSON, default=dict)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ─── Relationships ────────────────────────────────────────────────────────
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="payments")


class PayrollRecord(BaseModel, TimestampMixin):
    """Monthly payroll record for a teacher."""

    __tablename__ = "payroll_records"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "teacher_id", "period_month", "period_year",
            name="uq_payroll_teacher_period",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teachers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    period_month: Mapped[int] = mapped_column(Integer, nullable=False)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)

    base_salary: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    allowances: Mapped[dict] = mapped_column(JSON, default=dict)
    deductions: Mapped[dict] = mapped_column(JSON, default=dict)
    net_salary: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)

    status: Mapped[PayrollStatus] = mapped_column(
        String(20), nullable=False, default=PayrollStatus.DRAFT
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# SQLAlchemy needs this import here due to relationship back-reference
from sqlalchemy.orm import relationship  # noqa: E402
