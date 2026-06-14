from __future__ import annotations

import io
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select

from app.api.deps import get_current_active_user, require_roles
from app.core.database import AsyncSession, get_db
from app.domains.hr.models import EmployeeContract
from app.domains.hr.schemas import (
    ContractCreate,
    ContractResponse,
    ContractUpdate,
    PayrollPreviewRequest,
    PayrollPreviewResponse,
    PayrollRecordResponse,
    PayrollRunCreate,
    PayrollRunResponse,
)
from app.domains.hr.service import ContractService, PayrollRunService
from app.domains.tenants.models import Tenant
from app.domains.users.models import User
from app.shared.base_schema import PaginatedResponse
from app.shared.enums import ContractStatus, PayrollRunStatus, UserRole
from app.shared.pagination import PaginationParams, get_pagination_params

router = APIRouter()

_WRITE_ROLES = (UserRole.TENANT_ADMIN, UserRole.FINANCE_STAFF, UserRole.SUPER_ADMIN)
_ADMIN_ROLES = (UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN)


async def _user_name_map(db: AsyncSession, user_ids: list[uuid.UUID]) -> dict[str, str]:
    if not user_ids:
        return {}
    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    return {str(u.id): u.full_name for u in result.scalars().all()}


async def _enrich_records(
    db: AsyncSession,
    records: list[PayrollRecordResponse],
    tenant_id: uuid.UUID,
) -> list[PayrollRecordResponse]:
    name_map = await _user_name_map(db, [r.teacher_id for r in records])
    for rec in records:
        rec.employee_name = name_map.get(str(rec.teacher_id))
    return records


# ─── Staff eligible for contracts ─────────────────────────────────────────────

# Roles that count as "employees" in a tenant context (teachers, admin staff, etc.)
_TENANT_STAFF_ROLES = [
    UserRole.TENANT_ADMIN, UserRole.OWNER, UserRole.TEACHER,
    UserRole.FINANCE_STAFF, UserRole.BOARDING_SUPERVISOR, UserRole.ADMIN_STAFF,
]

# Roles that count as "employees" in the platform context (SUPER_ADMIN manages ADMIN_APPS)
_PLATFORM_STAFF_ROLES = [UserRole.ADMIN_APPS]


@router.get("/staff")
async def list_eligible_staff(
    current_user: Annotated[User, Depends(require_roles(*_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = Query(default=None),
) -> list[dict]:
    is_platform_admin = current_user.tenant_id is None
    eligible_roles = _PLATFORM_STAFF_ROLES if is_platform_admin else _TENANT_STAFF_ROLES

    stmt = (
        select(User)
        .where(User.is_deleted.is_(False), User.role.in_(eligible_roles))
        .order_by(User.full_name)
    )
    if not is_platform_admin:
        stmt = stmt.where(User.tenant_id == current_user.tenant_id)

    # Exclude users who already have an active contract in this scope
    already_contracted = (
        select(EmployeeContract.user_id)
        .where(EmployeeContract.status == ContractStatus.ACTIVE)
        .where(EmployeeContract.tenant_id == current_user.tenant_id)
    )
    stmt = stmt.where(User.id.not_in(already_contracted))

    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(User.full_name.ilike(like), User.email.ilike(like)))
    stmt = stmt.limit(200)
    result = await db.execute(stmt)
    users = result.scalars().all()
    return [
        {"id": str(u.id), "full_name": u.full_name, "email": u.email, "role": u.role}
        for u in users
    ]


# ─── Contracts ────────────────────────────────────────────────────────────────

@router.get("/contracts", response_model=PaginatedResponse[ContractResponse])
async def list_contracts(
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    current_user: Annotated[User, Depends(require_roles(*_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: ContractStatus | None = Query(default=None, alias="status"),
) -> PaginatedResponse[ContractResponse]:
    service = ContractService(db)
    result = await service.list_contracts(
        tenant_id=current_user.tenant_id,
        status=status_filter,
        pagination=pagination,
    )
    name_map = await _user_name_map(db, [c.user_id for c in result.items])
    items = []
    for c in result.items:
        resp = ContractResponse.model_validate(c)
        resp.user_full_name = name_map.get(str(c.user_id))
        items.append(resp)
    return PaginatedResponse.create(
        items=items,
        total=result.total,
        page=result.page,
        size=result.size,
    )


@router.post("/contracts", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def create_contract(
    data: ContractCreate,
    current_user: Annotated[User, Depends(require_roles(*_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContractResponse:
    service = ContractService(db)
    contract = await service.create_contract(
        tenant_id=current_user.tenant_id,
        data=data,
        created_by_id=current_user.id,
    )
    return ContractResponse.model_validate(contract)


@router.get("/contracts/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(*_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContractResponse:
    service = ContractService(db)
    contract = await service.get_or_404(current_user.tenant_id, contract_id)
    resp = ContractResponse.model_validate(contract)
    name_map = await _user_name_map(db, [contract.user_id])
    resp.user_full_name = name_map.get(str(contract.user_id))
    return resp


@router.patch("/contracts/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: uuid.UUID,
    data: ContractUpdate,
    current_user: Annotated[User, Depends(require_roles(*_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContractResponse:
    service = ContractService(db)
    contract = await service.update_contract(current_user.tenant_id, contract_id, data)
    return ContractResponse.model_validate(contract)


@router.delete("/contracts/{contract_id}", response_model=ContractResponse)
async def terminate_contract(
    contract_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(*_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContractResponse:
    service = ContractService(db)
    contract = await service.terminate_contract(current_user.tenant_id, contract_id)
    return ContractResponse.model_validate(contract)


# ─── Payroll Runs ─────────────────────────────────────────────────────────────

@router.get("/payroll/runs/preview", response_model=PayrollPreviewResponse)
async def preview_payroll(
    current_user: Annotated[User, Depends(require_roles(*_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
    period_month: int = Query(..., ge=1, le=12),
    period_year: int = Query(..., ge=2000, le=2100),
) -> PayrollPreviewResponse:
    service = PayrollRunService(db)
    request = PayrollPreviewRequest(
        period_month=period_month,
        period_year=period_year,
    )
    return await service.preview_payroll(current_user.tenant_id, request)


@router.get("/payroll/runs", response_model=PaginatedResponse[PayrollRunResponse])
async def list_payroll_runs(
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    current_user: Annotated[User, Depends(require_roles(*_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaginatedResponse[PayrollRunResponse]:
    service = PayrollRunService(db)
    result = await service.list_runs(
        tenant_id=current_user.tenant_id,
        pagination=pagination,
    )
    return PaginatedResponse.create(
        items=[PayrollRunResponse.model_validate(r) for r in result.items],
        total=result.total,
        page=result.page,
        size=result.size,
    )


@router.post("/payroll/runs", response_model=PayrollRunResponse, status_code=status.HTTP_201_CREATED)
async def create_payroll_run(
    data: PayrollRunCreate,
    current_user: Annotated[User, Depends(require_roles(*_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PayrollRunResponse:
    service = PayrollRunService(db)
    run = await service.create_run(
        tenant_id=current_user.tenant_id,
        data=data,
        run_by_id=current_user.id,
    )
    run_detail, records = await service.get_run_detail(current_user.tenant_id, run.id)
    response = PayrollRunResponse.model_validate(run_detail)
    response.records = await _enrich_records(
        db, [PayrollRecordResponse.model_validate(r) for r in records], current_user.tenant_id
    )
    return response


@router.get("/payroll/runs/{run_id}", response_model=PayrollRunResponse)
async def get_payroll_run(
    run_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(*_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PayrollRunResponse:
    service = PayrollRunService(db)
    run, records = await service.get_run_detail(current_user.tenant_id, run_id)
    response = PayrollRunResponse.model_validate(run)
    response.records = await _enrich_records(
        db, [PayrollRecordResponse.model_validate(r) for r in records], current_user.tenant_id
    )
    return response


@router.post("/payroll/runs/{run_id}/approve", response_model=PayrollRunResponse)
async def approve_payroll_run(
    run_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(*_ADMIN_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PayrollRunResponse:
    service = PayrollRunService(db)
    run = await service.approve_run(current_user.tenant_id, run_id, current_user.id)
    run_detail, records = await service.get_run_detail(current_user.tenant_id, run.id)
    response = PayrollRunResponse.model_validate(run_detail)
    response.records = await _enrich_records(
        db, [PayrollRecordResponse.model_validate(r) for r in records], current_user.tenant_id
    )
    return response


@router.post("/payroll/runs/{run_id}/pay", response_model=PayrollRunResponse)
async def mark_payroll_paid(
    run_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(*_WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PayrollRunResponse:
    service = PayrollRunService(db)
    run = await service.mark_paid(current_user.tenant_id, run_id)
    run_detail, records = await service.get_run_detail(current_user.tenant_id, run.id)
    response = PayrollRunResponse.model_validate(run_detail)
    response.records = await _enrich_records(
        db, [PayrollRecordResponse.model_validate(r) for r in records], current_user.tenant_id
    )
    return response


@router.post("/payroll/runs/{run_id}/cancel", response_model=PayrollRunResponse)
async def cancel_payroll_run(
    run_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(*_ADMIN_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PayrollRunResponse:
    service = PayrollRunService(db)
    run = await service.cancel_run(current_user.tenant_id, run_id)
    run_detail, records = await service.get_run_detail(current_user.tenant_id, run.id)
    response = PayrollRunResponse.model_validate(run_detail)
    response.records = await _enrich_records(
        db, [PayrollRecordResponse.model_validate(r) for r in records], current_user.tenant_id
    )
    return response


@router.get("/payroll/runs/{run_id}/payslips/{record_id}")
async def download_payslip(
    run_id: uuid.UUID,
    record_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    service = PayrollRunService(db)
    run, records = await service.get_run_detail(current_user.tenant_id, run_id)

    if run.status not in (PayrollRunStatus.APPROVED, PayrollRunStatus.PAID):
        raise HTTPException(status_code=409, detail="Payslips are only available for approved or paid runs.")

    record = next((r for r in records if r.id == record_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="Payroll record not found.")

    # Allow download only if: admin/finance role OR this is the user's own payslip
    if current_user.role not in _WRITE_ROLES:
        if record.teacher_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only download your own payslip.",
            )

    # Fetch employee user
    user_res = await db.execute(select(User).where(User.id == record.teacher_id))
    employee = user_res.scalar_one_or_none()
    employee_name = employee.full_name if employee else str(record.teacher_id)

    # Fetch contract for position/department/employment_type info
    contract: EmployeeContract | None = None
    if record.contract_id:
        contract_res = await db.execute(
            select(EmployeeContract).where(EmployeeContract.id == record.contract_id)
        )
        contract = contract_res.scalar_one_or_none()

    # Fetch tenant name
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    school_name = tenant.name if tenant else "Boarding School"

    allowances_raw: list[dict] = []
    if record.allowances and isinstance(record.allowances, dict):
        allowances_raw = record.allowances.get("items", [])

    from app.domains.hr.payslip_generator import render_payslip_pdf

    pdf_bytes = render_payslip_pdf(
        school_name=school_name,
        employee_name=employee_name,
        employee_number=contract.employee_number if contract else None,
        position=contract.position if contract else None,
        department=contract.department if contract else None,
        employment_type=(
            contract.employment_type.value
            if contract and hasattr(contract.employment_type, "value")
            else (str(contract.employment_type) if contract else "—")
        ),
        period_month=record.period_month,
        period_year=record.period_year,
        base_salary=float(record.base_salary),
        allowances=allowances_raw,
        gross_salary=float(record.gross_salary or record.base_salary),
        tax_amount=float(record.tax_amount or 0),
        bpjs_employee=float(record.bpjs_employee or 0),
        one_time_adjustments=record.one_time_adjustments or [],
        net_salary=float(record.net_salary),
    )

    safe_name = employee_name.replace(" ", "_")
    filename = f"payslip_{safe_name}_{record.period_year}-{record.period_month:02d}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
