from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.finance.models import PayrollRecord
from app.domains.hr.models import EmployeeContract, PayrollRun
from app.domains.hr.repository import ContractRepository, PayrollRecordRepository, PayrollRunRepository
from app.domains.hr.schemas import (
    ContractCreate,
    ContractUpdate,
    EmployeePreviewRow,
    MissingContractEntry,
    OneTimeAdjustment,
    PayrollPreviewRequest,
    PayrollPreviewResponse,
    PayrollRunCreate,
)
from app.domains.hr.tax_tables import (
    calculate_bpjs_employee,
    calculate_bpjs_employer,
    calculate_pph21,
)
from app.domains.users.models import User
from app.shared.base_schema import PaginatedResponse
from app.shared.enums import ContractStatus, PayrollRunStatus, UserRole
from app.shared.pagination import PaginationParams

logger = structlog.get_logger(__name__)

# Roles treated as employees for the purpose of payroll contract-gate checking
_EMPLOYEE_ROLES: frozenset[UserRole] = frozenset(
    [
        UserRole.TEACHER,
        UserRole.ADMIN_STAFF,
        UserRole.BOARDING_SUPERVISOR,
        UserRole.FINANCE_STAFF,
        UserRole.TENANT_ADMIN,
        UserRole.OWNER,
    ]
)


class ContractService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ContractRepository(session)

    async def create_contract(
        self,
        tenant_id: uuid.UUID | None,
        data: ContractCreate,
        created_by_id: uuid.UUID,
    ) -> EmployeeContract:
        # Rule: validate user belongs to this tenant
        user = await self._get_user_in_tenant(data.user_id, tenant_id)
        if user is None:
            raise HTTPException(status_code=422, detail="User not found in this tenant.")

        # Rule: no existing active contract for same user
        existing = await self.repo.get_active_contract_for_user(tenant_id, data.user_id)
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=f"An active contract already exists for this employee (contract id: {existing.id}).",
            )

        contract_data = data.model_dump()
        # Serialise allowances list to plain dicts for JSONB storage
        contract_data["allowances"] = [
            a.model_dump() if hasattr(a, "model_dump") else a
            for a in (data.allowances or [])
        ]
        contract_data["tenant_id"] = tenant_id
        contract_data["created_by"] = created_by_id

        contract = EmployeeContract(**contract_data)
        self.session.add(contract)
        await self.session.flush()
        await self.session.refresh(contract)

        logger.info(
            "contract.created",
            contract_id=str(contract.id),
            tenant_id=str(tenant_id),
            user_id=str(data.user_id),
        )
        return contract

    async def update_contract(
        self,
        tenant_id: uuid.UUID | None,
        contract_id: uuid.UUID,
        data: ContractUpdate,
    ) -> EmployeeContract:
        contract = await self.get_or_404(tenant_id, contract_id)
        update_data = data.model_dump(exclude_unset=True)

        if "allowances" in update_data and update_data["allowances"] is not None:
            update_data["allowances"] = [
                a.model_dump() if hasattr(a, "model_dump") else a
                for a in update_data["allowances"]
            ]

        for field, value in update_data.items():
            setattr(contract, field, value)

        self.session.add(contract)
        await self.session.flush()
        await self.session.refresh(contract)
        return contract

    async def terminate_contract(
        self,
        tenant_id: uuid.UUID | None,
        contract_id: uuid.UUID,
    ) -> EmployeeContract:
        contract = await self.get_or_404(tenant_id, contract_id)
        if contract.status == ContractStatus.TERMINATED:
            raise HTTPException(status_code=409, detail="Contract is already terminated.")
        contract.status = ContractStatus.TERMINATED
        self.session.add(contract)
        await self.session.flush()
        await self.session.refresh(contract)
        logger.info("contract.terminated", contract_id=str(contract_id), tenant_id=str(tenant_id))
        return contract

    async def list_contracts(
        self,
        tenant_id: uuid.UUID | None,
        status: ContractStatus | None,
        pagination: PaginationParams,
    ) -> PaginatedResponse[EmployeeContract]:
        items, total = await self.repo.list_by_tenant(
            tenant_id=tenant_id,
            status=status,
            skip=pagination.offset,
            limit=pagination.size,
        )
        return PaginatedResponse.create(items=items, total=total, page=pagination.page, size=pagination.size)

    async def get_or_404(
        self,
        tenant_id: uuid.UUID | None,
        contract_id: uuid.UUID,
    ) -> EmployeeContract:
        contract = await self.repo.get_by_tenant(contract_id, tenant_id)
        if contract is None:
            raise HTTPException(status_code=404, detail="Contract not found.")
        return contract

    async def _get_user_in_tenant(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID | None,
    ) -> User | None:
        stmt = select(User).where(
            and_(
                User.id == user_id,
                User.tenant_id == tenant_id,
                User.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class PayrollRunService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.run_repo = PayrollRunRepository(session)
        self.contract_repo = ContractRepository(session)
        self.record_repo = PayrollRecordRepository(session)

    async def preview_payroll(
        self,
        tenant_id: uuid.UUID | None,
        request: PayrollPreviewRequest,
    ) -> PayrollPreviewResponse:
        """Calculate payroll figures without persisting anything."""
        employees = await self._get_tenant_employees(tenant_id)
        missing, employee_rows = await self._calculate_employee_rows(
            tenant_id=tenant_id,
            employees=employees,
            adjustments_map=request.one_time_adjustments,
        )

        if missing:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Cannot run payroll: employees missing contracts",
                    "employees_without_contracts": [e.model_dump() for e in missing],
                },
            )

        total_gross = sum(r.gross_salary for r in employee_rows)
        total_deductions = sum(r.tax_amount + r.bpjs_employee + r.other_deductions for r in employee_rows)
        total_net = sum(r.net_salary for r in employee_rows)

        return PayrollPreviewResponse(
            period_month=request.period_month,
            period_year=request.period_year,
            employees=employee_rows,
            total_gross=round(total_gross, 2),
            total_deductions=round(total_deductions, 2),
            total_net=round(total_net, 2),
        )

    async def create_run(
        self,
        tenant_id: uuid.UUID | None,
        data: PayrollRunCreate,
        run_by_id: uuid.UUID,
    ) -> PayrollRun:
        # Duplicate period check
        existing_run = await self.run_repo.get_run_for_period(
            tenant_id, data.period_month, data.period_year
        )
        if existing_run is not None:
            raise HTTPException(
                status_code=409,
                detail=f"A payroll run for {data.period_month}/{data.period_year} already exists (id: {existing_run.id}).",
            )

        employees = await self._get_tenant_employees(tenant_id)

        # Parse per-employee adjustments from the raw dict
        adjustments_map: dict[str, list[OneTimeAdjustment]] = {}
        for user_id_str, adj_list in (data.one_time_adjustments or {}).items():
            if isinstance(adj_list, list):
                adjustments_map[user_id_str] = [
                    OneTimeAdjustment(**a) if isinstance(a, dict) else a
                    for a in adj_list
                ]

        missing, employee_rows = await self._calculate_employee_rows(
            tenant_id=tenant_id,
            employees=employees,
            adjustments_map=adjustments_map,
        )

        if missing:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Cannot run payroll: employees missing contracts",
                    "employees_without_contracts": [e.model_dump() for e in missing],
                },
            )

        total_gross = round(sum(r.gross_salary for r in employee_rows), 2)
        total_deductions = round(
            sum(r.tax_amount + r.bpjs_employee + r.other_deductions for r in employee_rows), 2
        )
        total_net = round(sum(r.net_salary for r in employee_rows), 2)

        now = datetime.now(UTC)
        run = PayrollRun(
            tenant_id=tenant_id,
            period_month=data.period_month,
            period_year=data.period_year,
            status=PayrollRunStatus.DRAFT,
            total_gross=total_gross,
            total_deductions=total_deductions,
            total_net=total_net,
            run_by=run_by_id,
            run_at=now,
            notes=data.notes,
        )
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)

        # Build contract lookup once to avoid N+1
        contract_map = await self._build_contract_map(tenant_id, employees)

        for row in employee_rows:
            contract = contract_map.get(str(row.user_id))
            # teacher_id field on PayrollRecord is a legacy FK to teachers.id;
            # use user_id as a best-effort substitution — the new contract_id FK provides the canonical link
            record = PayrollRecord(
                tenant_id=tenant_id,
                teacher_id=row.user_id,
                contract_id=contract.id if contract else None,
                payroll_run_id=run.id,
                period_month=data.period_month,
                period_year=data.period_year,
                base_salary=row.base_salary,
                gross_salary=row.gross_salary,
                allowances_total=row.allowances_total,
                tax_amount=row.tax_amount,
                bpjs_employee=row.bpjs_employee,
                bpjs_employer=row.bpjs_employer,
                other_deductions=row.other_deductions,
                allowances={"items": contract.allowances if contract else []},
                deductions={},
                net_salary=row.net_salary,
                one_time_adjustments=[
                    a.model_dump() if hasattr(a, "model_dump") else a
                    for a in (adjustments_map.get(str(row.user_id)) or [])
                ],
            )
            self.session.add(record)

        await self.session.flush()

        logger.info(
            "payroll_run.created",
            run_id=str(run.id),
            tenant_id=str(tenant_id),
            period=f"{data.period_month}/{data.period_year}",
            employee_count=len(employee_rows),
        )
        return run

    async def approve_run(
        self,
        tenant_id: uuid.UUID | None,
        run_id: uuid.UUID,
        approved_by_id: uuid.UUID,
    ) -> PayrollRun:
        run = await self._get_run_or_404(tenant_id, run_id)
        if run.status != PayrollRunStatus.DRAFT:
            raise HTTPException(status_code=409, detail="Only draft runs can be approved.")
        run.status = PayrollRunStatus.APPROVED
        run.approved_by = approved_by_id
        run.approved_at = datetime.now(UTC)
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        logger.info("payroll_run.approved", run_id=str(run_id), tenant_id=str(tenant_id))
        return run

    async def mark_paid(
        self,
        tenant_id: uuid.UUID | None,
        run_id: uuid.UUID,
    ) -> PayrollRun:
        run = await self._get_run_or_404(tenant_id, run_id)
        if run.status != PayrollRunStatus.APPROVED:
            raise HTTPException(status_code=409, detail="Only approved runs can be marked as paid.")
        run.status = PayrollRunStatus.PAID
        run.paid_at = datetime.now(UTC)
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        logger.info("payroll_run.paid", run_id=str(run_id), tenant_id=str(tenant_id))
        return run

    async def cancel_run(
        self,
        tenant_id: uuid.UUID | None,
        run_id: uuid.UUID,
    ) -> PayrollRun:
        run = await self._get_run_or_404(tenant_id, run_id)
        if run.status == PayrollRunStatus.PAID:
            raise HTTPException(status_code=409, detail="Paid payroll runs cannot be cancelled.")
        if run.status == PayrollRunStatus.CANCELLED:
            raise HTTPException(status_code=409, detail="Run is already cancelled.")
        run.status = PayrollRunStatus.CANCELLED
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        logger.info("payroll_run.cancelled", run_id=str(run_id), tenant_id=str(tenant_id))
        return run

    async def get_run_detail(
        self,
        tenant_id: uuid.UUID | None,
        run_id: uuid.UUID,
    ) -> tuple[PayrollRun, list[PayrollRecord]]:
        run = await self._get_run_or_404(tenant_id, run_id)
        records = await self.record_repo.get_records_for_run(run_id, tenant_id)
        return run, records

    async def list_runs(
        self,
        tenant_id: uuid.UUID | None,
        pagination: PaginationParams,
    ) -> PaginatedResponse[PayrollRun]:
        items, total = await self.run_repo.list_by_tenant(
            tenant_id=tenant_id,
            skip=pagination.offset,
            limit=pagination.size,
        )
        return PaginatedResponse.create(items=items, total=total, page=pagination.page, size=pagination.size)

    async def _get_run_or_404(self, tenant_id: uuid.UUID | None, run_id: uuid.UUID) -> PayrollRun:
        run = await self.run_repo.get_by_tenant(run_id, tenant_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Payroll run not found.")
        return run

    async def _get_tenant_employees(self, tenant_id: uuid.UUID | None) -> list[User]:
        """Return all active employees (staff roles) for the tenant."""
        stmt = select(User).where(
            and_(
                User.tenant_id == tenant_id,
                User.is_active.is_(True),
                User.is_deleted.is_(False),
                User.role.in_([r.value for r in _EMPLOYEE_ROLES]),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _build_contract_map(
        self,
        tenant_id: uuid.UUID | None,
        employees: list[User],
    ) -> dict[str, EmployeeContract]:
        """Return a mapping from user_id string to their active contract."""
        result: dict[str, EmployeeContract] = {}
        for emp in employees:
            contract = await self.contract_repo.get_active_contract_for_user(tenant_id, emp.id)
            if contract:
                result[str(emp.id)] = contract
        return result

    async def _calculate_employee_rows(
        self,
        tenant_id: uuid.UUID | None,
        employees: list[User],
        adjustments_map: dict[str, list[OneTimeAdjustment]],
    ) -> tuple[list[MissingContractEntry], list[EmployeePreviewRow]]:
        """
        For each employee resolve their contract and compute pay figures.

        Returns a tuple of (missing_contract_entries, calculated_rows).
        If any missing entries exist, the payroll cannot proceed.
        """
        missing: list[MissingContractEntry] = []
        rows: list[EmployeePreviewRow] = []

        for emp in employees:
            contract = await self.contract_repo.get_active_contract_for_user(tenant_id, emp.id)
            if contract is None:
                missing.append(
                    MissingContractEntry(
                        user_id=emp.id,
                        full_name=emp.full_name,
                        role=emp.role.value if hasattr(emp.role, "value") else str(emp.role),
                    )
                )
                continue

            employee_adjustments = adjustments_map.get(str(emp.id), [])
            row = _compute_payroll_row(emp, contract, employee_adjustments)
            rows.append(row)

        return missing, rows


def _compute_payroll_row(
    user: User,
    contract: EmployeeContract,
    adjustments: list[OneTimeAdjustment],
) -> EmployeePreviewRow:
    """Compute all pay components for one employee based on their contract."""
    allowances_list = contract.allowances if isinstance(contract.allowances, list) else []
    allowances_total = sum(float(a.get("amount", 0)) for a in allowances_list)

    one_time_additions = sum(
        a.amount for a in adjustments if a.type == "addition"
    )
    one_time_deductions = sum(
        a.amount for a in adjustments if a.type == "deduction"
    )

    gross = float(contract.base_salary) + allowances_total + one_time_additions

    emp_type = (
        contract.employment_type.value
        if hasattr(contract.employment_type, "value")
        else str(contract.employment_type)
    )
    tax = calculate_pph21(gross, emp_type, contract.tax_config)
    bpjs_emp = calculate_bpjs_employee(gross, emp_type, contract.insurance_config)
    bpjs_er = calculate_bpjs_employer(gross, emp_type, contract.insurance_config)

    net = gross - tax - bpjs_emp - one_time_deductions

    return EmployeePreviewRow(
        user_id=user.id,
        full_name=user.full_name,
        employment_type=emp_type,
        base_salary=float(contract.base_salary),
        allowances_total=round(allowances_total, 2),
        gross_salary=round(gross, 2),
        tax_amount=tax,
        bpjs_employee=bpjs_emp,
        bpjs_employer=bpjs_er,
        other_deductions=round(one_time_deductions, 2),
        net_salary=round(net, 2),
    )
