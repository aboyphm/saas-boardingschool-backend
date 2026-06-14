from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domains.finance.models import FeeCategory, Invoice, Payment, PayrollRecord
from app.domains.finance.repository import (
    FeeCategoryRepository,
    InvoiceRepository,
    PaymentRepository,
    PayrollRepository,
)
from app.domains.finance.schemas import (
    FeeCategoryCreate,
    FeeCategoryUpdate,
    InvoiceCreate,
    PaymentCreate,
    PayrollCreate,
    RevenueReportResponse,
)
from app.shared.enums import InvoiceStatus, PayrollStatus
from app.shared.pagination import PaginationParams


class FinanceService:
    def __init__(
        self,
        fee_repo: FeeCategoryRepository,
        invoice_repo: InvoiceRepository,
        payment_repo: PaymentRepository,
        payroll_repo: PayrollRepository,
    ) -> None:
        self.fee_repo = fee_repo
        self.invoice_repo = invoice_repo
        self.payment_repo = payment_repo
        self.payroll_repo = payroll_repo

    # ─── Fee categories ───────────────────────────────────────────────────────
    async def create_fee_category(self, data: FeeCategoryCreate) -> FeeCategory:
        category = FeeCategory(**data.model_dump())
        self.fee_repo.session.add(category)
        await self.fee_repo.session.flush()
        await self.fee_repo.session.refresh(category)
        return category

    async def list_fee_categories(self, tenant_id: uuid.UUID) -> list[FeeCategory]:
        return await self.fee_repo.list(filters={"tenant_id": tenant_id})

    async def update_fee_category(
        self,
        category_id: uuid.UUID,
        data: FeeCategoryUpdate,
        tenant_id: uuid.UUID,
    ) -> FeeCategory:
        category = await self.fee_repo.get_by_tenant(category_id, tenant_id)
        if category is None:
            raise NotFoundError("Fee category not found.")
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(category, field, value)
        await self.fee_repo.session.flush()
        await self.fee_repo.session.refresh(category)
        return category

    async def delete_fee_category(
        self, category_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        category = await self.fee_repo.get_by_tenant(category_id, tenant_id)
        if category is None:
            raise NotFoundError("Fee category not found.")
        await self.fee_repo.session.delete(category)
        await self.fee_repo.session.flush()

    # ─── Invoices ─────────────────────────────────────────────────────────────
    async def create_invoice(self, data: InvoiceCreate, created_by: uuid.UUID) -> Invoice:
        invoice_number = await self.invoice_repo.get_next_invoice_number(data.tenant_id)

        # Calculate totals from line items
        subtotal = sum(item.total for item in data.items)
        tax_amount = round(subtotal * (data.tax_rate / 100), 2)
        total_amount = subtotal - data.discount + tax_amount

        invoice = Invoice(
            tenant_id=data.tenant_id,
            student_id=data.student_id,
            invoice_number=invoice_number,
            title=data.title,
            description=data.description,
            items=[item.model_dump() for item in data.items],
            subtotal=subtotal,
            discount=data.discount,
            tax_rate=data.tax_rate,
            tax_amount=tax_amount,
            total_amount=total_amount,
            due_date=data.due_date,
            notes=data.notes,
            status=InvoiceStatus.DRAFT,
        )
        self.invoice_repo.session.add(invoice)
        await self.invoice_repo.session.flush()
        await self.invoice_repo.session.refresh(invoice)
        return invoice

    async def get_invoice_or_404(
        self, invoice_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Invoice:
        invoice = await self.invoice_repo.get_by_tenant(invoice_id, tenant_id)
        if invoice is None:
            raise NotFoundError("Invoice not found.")
        return invoice

    async def list_invoices(
        self,
        tenant_id: uuid.UUID,
        pagination: PaginationParams,
        status: InvoiceStatus | None = None,
    ) -> tuple[list[Invoice], int]:
        filters: dict = {"tenant_id": tenant_id}
        if status is not None:
            filters["status"] = status
        items = await self.invoice_repo.list(
            filters=filters, skip=pagination.offset, limit=pagination.size
        )
        total = await self.invoice_repo.count(filters=filters)
        return items, total

    async def send_invoice(self, invoice_id: uuid.UUID, tenant_id: uuid.UUID) -> Invoice:
        invoice = await self.get_invoice_or_404(invoice_id, tenant_id)
        if invoice.status not in (InvoiceStatus.DRAFT,):
            raise ValidationError("Only draft invoices can be sent.")
        invoice.status = InvoiceStatus.SENT
        self.invoice_repo.session.add(invoice)
        await self.invoice_repo.session.flush()
        await self.invoice_repo.session.refresh(invoice)
        # TODO: Enqueue send_whatsapp_notification or send_email_notification task
        return invoice

    # ─── Payments ─────────────────────────────────────────────────────────────
    async def record_payment(
        self, data: PaymentCreate, recorded_by: uuid.UUID
    ) -> Payment:
        invoice = await self.get_invoice_or_404(data.invoice_id, data.tenant_id)
        if invoice.status == InvoiceStatus.PAID:
            raise ConflictError("Invoice is already fully paid.")

        payment = Payment(
            tenant_id=data.tenant_id,
            invoice_id=data.invoice_id,
            amount=data.amount,
            payment_method=data.payment_method,
            payment_reference=data.payment_reference,
            paid_at=data.paid_at or datetime.now(UTC),
            recorded_by=recorded_by,
        )
        self.payment_repo.session.add(payment)

        # Mark invoice as paid if amount covers the total
        total_paid = sum(
            p.amount for p in await self.payment_repo.list_by_invoice(invoice.id)
        ) + data.amount
        if total_paid >= invoice.total_amount:
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = datetime.now(UTC)
            self.invoice_repo.session.add(invoice)

        await self.payment_repo.session.flush()
        await self.payment_repo.session.refresh(payment)
        return payment

    # ─── Revenue reporting ────────────────────────────────────────────────────
    async def get_revenue_report(self, tenant_id: uuid.UUID) -> RevenueReportResponse:
        stats = await self.invoice_repo.get_revenue_stats(tenant_id)
        invoiced = sum(v["total"] for v in stats.values())
        collected = stats.get(InvoiceStatus.PAID, {}).get("total", 0.0)
        outstanding = stats.get(InvoiceStatus.OVERDUE, {}).get("total", 0.0)
        rate = (collected / invoiced * 100) if invoiced > 0 else 0.0
        total_invoices = sum(v["count"] for v in stats.values())
        return RevenueReportResponse(
            period="all-time",
            total_invoiced=invoiced,
            total_collected=collected,
            total_outstanding=outstanding,
            collection_rate=round(rate, 2),
            invoice_count=total_invoices,
            payment_count=0,
        )

    # ─── Payroll ──────────────────────────────────────────────────────────────
    async def create_payroll(self, data: PayrollCreate) -> PayrollRecord:
        existing = await self.payroll_repo.exists({
            "tenant_id": data.tenant_id,
            "teacher_id": data.teacher_id,
            "period_month": data.period_month,
            "period_year": data.period_year,
        })
        if existing:
            raise ConflictError("Payroll record for this period already exists.")

        total_allowances = sum(data.allowances.values()) if data.allowances else 0
        total_deductions = sum(data.deductions.values()) if data.deductions else 0
        net_salary = data.base_salary + total_allowances - total_deductions

        record = PayrollRecord(
            **data.model_dump(),
            net_salary=net_salary,
        )
        self.payroll_repo.session.add(record)
        await self.payroll_repo.session.flush()
        await self.payroll_repo.session.refresh(record)
        return record

    async def list_payroll(
        self, tenant_id: uuid.UUID, pagination: PaginationParams
    ) -> tuple[list[PayrollRecord], int]:
        items = await self.payroll_repo.list(
            filters={"tenant_id": tenant_id},
            skip=pagination.offset,
            limit=pagination.size,
        )
        total = await self.payroll_repo.count(filters={"tenant_id": tenant_id})
        return items, total
