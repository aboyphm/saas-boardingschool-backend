from __future__ import annotations

import uuid
from datetime import date, datetime

from app.shared.base_schema import BaseSchema
from app.shared.enums import BillingCycle, InvoiceStatus, PayrollStatus


class FeeCategoryCreate(BaseSchema):
    tenant_id: uuid.UUID
    name: str
    description: str | None = None
    amount: float
    is_recurring: bool = False
    billing_cycle: BillingCycle = BillingCycle.MONTHLY


class FeeCategoryUpdate(BaseSchema):
    name: str | None = None
    description: str | None = None
    amount: float | None = None
    billing_cycle: BillingCycle | None = None


class FeeCategoryResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    amount: float
    is_recurring: bool
    billing_cycle: BillingCycle
    created_at: datetime


class InvoiceLineItem(BaseSchema):
    name: str
    quantity: int = 1
    unit_price: float
    total: float


class InvoiceCreate(BaseSchema):
    tenant_id: uuid.UUID
    student_id: uuid.UUID
    title: str
    description: str | None = None
    items: list[InvoiceLineItem]
    discount: float = 0
    tax_rate: float = 0
    due_date: date
    notes: str | None = None


class InvoiceUpdate(BaseSchema):
    title: str | None = None
    description: str | None = None
    notes: str | None = None
    due_date: date | None = None
    status: InvoiceStatus | None = None


class InvoiceResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    student_id: uuid.UUID
    invoice_number: str
    title: str
    description: str | None
    subtotal: float
    discount: float
    tax_rate: float
    tax_amount: float
    total_amount: float
    due_date: date
    status: InvoiceStatus
    paid_at: datetime | None
    notes: str | None
    items: list
    created_at: datetime


class PaymentCreate(BaseSchema):
    tenant_id: uuid.UUID
    invoice_id: uuid.UUID
    amount: float
    payment_method: str
    payment_reference: str | None = None
    paid_at: datetime | None = None


class PaymentResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    invoice_id: uuid.UUID
    amount: float
    payment_method: str
    payment_reference: str | None
    paid_at: datetime
    created_at: datetime


class PayrollCreate(BaseSchema):
    tenant_id: uuid.UUID
    teacher_id: uuid.UUID
    period_month: int
    period_year: int
    base_salary: float
    allowances: dict = {}
    deductions: dict = {}


class PayrollResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    teacher_id: uuid.UUID
    period_month: int
    period_year: int
    base_salary: float
    allowances: dict
    deductions: dict
    net_salary: float
    status: PayrollStatus
    paid_at: datetime | None
    created_at: datetime


class RevenueReportResponse(BaseSchema):
    period: str
    total_invoiced: float
    total_collected: float
    total_outstanding: float
    collection_rate: float
    invoice_count: int
    payment_count: int
