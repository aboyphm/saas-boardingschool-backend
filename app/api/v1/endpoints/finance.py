from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import require_roles
from app.core.database import AsyncSession, get_db
from app.domains.finance.repository import (
    FeeCategoryRepository,
    InvoiceRepository,
    PaymentRepository,
    PayrollRepository,
)
from app.domains.finance.schemas import (
    FeeCategoryCreate,
    FeeCategoryResponse,
    FeeCategoryUpdate,
    InvoiceCreate,
    InvoiceResponse,
    PaymentCreate,
    PaymentResponse,
    PayrollCreate,
    PayrollResponse,
    RevenueReportResponse,
)
from app.domains.finance.service import FinanceService
from app.domains.users.models import User
from app.shared.base_schema import PaginatedResponse
from app.shared.enums import InvoiceStatus, UserRole
from app.shared.pagination import PaginationParams, get_pagination_params

router = APIRouter()


def _get_service(db: AsyncSession) -> FinanceService:
    return FinanceService(
        fee_repo=FeeCategoryRepository(db),
        invoice_repo=InvoiceRepository(db),
        payment_repo=PaymentRepository(db),
        payroll_repo=PayrollRepository(db),
    )


# ─── Fee categories ───────────────────────────────────────────────────────────
@router.get("/fee-categories", response_model=list[FeeCategoryResponse])
async def list_fee_categories(
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.FINANCE_STAFF, UserRole.OWNER, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[FeeCategoryResponse]:
    if current_user.tenant_id is None:
        return []
    service = _get_service(db)
    items = await service.list_fee_categories(current_user.tenant_id)
    return [FeeCategoryResponse.model_validate(i) for i in items]


@router.post("/fee-categories", response_model=FeeCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_fee_category(
    data: FeeCategoryCreate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.FINANCE_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeeCategoryResponse:
    service = _get_service(db)
    category = await service.create_fee_category(data)
    return FeeCategoryResponse.model_validate(category)


@router.put("/fee-categories/{category_id}", response_model=FeeCategoryResponse)
async def update_fee_category(
    category_id: uuid.UUID,
    data: FeeCategoryUpdate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.FINANCE_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeeCategoryResponse:
    service = _get_service(db)
    category = await service.update_fee_category(
        category_id, data, current_user.tenant_id
    )
    return FeeCategoryResponse.model_validate(category)


@router.delete("/fee-categories/{category_id}", status_code=status.HTTP_200_OK)
async def delete_fee_category(
    category_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.FINANCE_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _get_service(db)
    await service.delete_fee_category(category_id, current_user.tenant_id)
    return {"ok": True}


# ─── Invoices ─────────────────────────────────────────────────────────────────
@router.get("/invoices", response_model=PaginatedResponse[InvoiceResponse])
async def list_invoices(
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.FINANCE_STAFF, UserRole.OWNER, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: InvoiceStatus | None = Query(default=None),
) -> PaginatedResponse[InvoiceResponse]:
    if current_user.tenant_id is None:
        return PaginatedResponse.create(items=[], total=0, page=1, size=pagination.size)
    service = _get_service(db)
    items, total = await service.list_invoices(current_user.tenant_id, pagination, status)
    return PaginatedResponse.create(
        items=[InvoiceResponse.model_validate(i) for i in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    data: InvoiceCreate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.FINANCE_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InvoiceResponse:
    service = _get_service(db)
    invoice = await service.create_invoice(data, created_by=current_user.id)
    return InvoiceResponse.model_validate(invoice)


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.FINANCE_STAFF, UserRole.OWNER, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InvoiceResponse:
    service = _get_service(db)
    invoice = await service.get_invoice_or_404(invoice_id, current_user.tenant_id)
    return InvoiceResponse.model_validate(invoice)


@router.post("/invoices/{invoice_id}/send", response_model=InvoiceResponse)
async def send_invoice(
    invoice_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.FINANCE_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InvoiceResponse:
    service = _get_service(db)
    invoice = await service.send_invoice(invoice_id, current_user.tenant_id)
    return InvoiceResponse.model_validate(invoice)


# ─── Payments ─────────────────────────────────────────────────────────────────
@router.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def record_payment(
    data: PaymentCreate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.FINANCE_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaymentResponse:
    service = _get_service(db)
    payment = await service.record_payment(data, recorded_by=current_user.id)
    return PaymentResponse.model_validate(payment)


# ─── Reports ──────────────────────────────────────────────────────────────────
@router.get("/report/revenue", response_model=RevenueReportResponse)
async def revenue_report(
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.FINANCE_STAFF, UserRole.OWNER, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RevenueReportResponse:
    service = _get_service(db)
    return await service.get_revenue_report(current_user.tenant_id)


# ─── Payroll ──────────────────────────────────────────────────────────────────
@router.post("/payroll", response_model=PayrollResponse, status_code=status.HTTP_201_CREATED)
async def create_payroll(
    data: PayrollCreate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.FINANCE_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PayrollResponse:
    service = _get_service(db)
    record = await service.create_payroll(data)
    return PayrollResponse.model_validate(record)


@router.get("/payroll", response_model=PaginatedResponse[PayrollResponse])
async def list_payroll(
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.FINANCE_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaginatedResponse[PayrollResponse]:
    service = _get_service(db)
    items, total = await service.list_payroll(current_user.tenant_id, pagination)
    return PaginatedResponse.create(
        items=[PayrollResponse.model_validate(p) for p in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )
