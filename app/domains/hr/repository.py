from __future__ import annotations

import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.finance.models import PayrollRecord
from app.domains.hr.models import EmployeeContract, PayrollRun
from app.domains.hr.schemas import ContractCreate, ContractUpdate, PayrollRunCreate, PayrollRunUpdate
from app.shared.base_repository import BaseRepository
from app.shared.enums import ContractStatus, PayrollRunStatus


class ContractRepository(BaseRepository[EmployeeContract, ContractCreate, ContractUpdate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(EmployeeContract, session)

    async def get_active_contract_for_user(
        self,
        tenant_id: uuid.UUID | None,
        user_id: uuid.UUID,
    ) -> EmployeeContract | None:
        """Return the single active contract for a user within a tenant, or None."""
        stmt = (
            self._base_query()
            .where(
                and_(
                    EmployeeContract.tenant_id == tenant_id,
                    EmployeeContract.user_id == user_id,
                    EmployeeContract.status == ContractStatus.ACTIVE,
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID | None,
        status: ContractStatus | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[EmployeeContract], int]:
        """Return a paginated list of contracts for a tenant, optionally filtered by status."""
        base = self._base_query().where(EmployeeContract.tenant_id == tenant_id)
        if status is not None:
            base = base.where(EmployeeContract.status == status)

        count_stmt = select(func.count()).select_from(base.subquery())
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        items_stmt = (
            base.order_by(EmployeeContract.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items_result = await self.session.execute(items_stmt)
        return list(items_result.scalars().all()), total


class PayrollRunRepository(BaseRepository[PayrollRun, PayrollRunCreate, PayrollRunUpdate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(PayrollRun, session)

    async def get_run_for_period(
        self,
        tenant_id: uuid.UUID | None,
        month: int,
        year: int,
    ) -> PayrollRun | None:
        """Return any non-cancelled run for the given period, or None."""
        stmt = (
            self._base_query()
            .where(
                and_(
                    PayrollRun.tenant_id == tenant_id,
                    PayrollRun.period_month == month,
                    PayrollRun.period_year == year,
                    PayrollRun.status != PayrollRunStatus.CANCELLED,
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID | None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[PayrollRun], int]:
        """Return a paginated list of payroll runs for a tenant."""
        base = self._base_query().where(PayrollRun.tenant_id == tenant_id)

        count_stmt = select(func.count()).select_from(base.subquery())
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        items_stmt = (
            base.order_by(PayrollRun.period_year.desc(), PayrollRun.period_month.desc())
            .offset(skip)
            .limit(limit)
        )
        items_result = await self.session.execute(items_stmt)
        return list(items_result.scalars().all()), total


class PayrollRecordRepository:
    """Provides HR-specific queries against the shared PayrollRecord table."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_records_for_run(
        self,
        payroll_run_id: uuid.UUID,
        tenant_id: uuid.UUID | None,
    ) -> list[PayrollRecord]:
        """Return all payroll records belonging to a given run."""
        stmt = select(PayrollRecord).where(
            and_(
                PayrollRecord.payroll_run_id == payroll_run_id,
                PayrollRecord.tenant_id == tenant_id,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
