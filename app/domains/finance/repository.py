from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.finance.models import FeeCategory, Invoice, Payment, PayrollRecord
from app.domains.finance.schemas import (
    FeeCategoryCreate,
    FeeCategoryUpdate,
    InvoiceCreate,
    InvoiceUpdate,
    PaymentCreate,
    PayrollCreate,
)
from app.shared.base_repository import BaseRepository
from app.shared.enums import InvoiceStatus


class FeeCategoryRepository(
    BaseRepository[FeeCategory, FeeCategoryCreate, FeeCategoryUpdate]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(FeeCategory, session)


class InvoiceRepository(BaseRepository[Invoice, InvoiceCreate, InvoiceUpdate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Invoice, session)

    async def list_by_student(
        self, student_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> list[Invoice]:
        stmt = (
            select(Invoice)
            .where(Invoice.student_id == student_id, Invoice.tenant_id == tenant_id)
            .order_by(Invoice.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_revenue_stats(self, tenant_id: uuid.UUID) -> dict:
        """Return aggregate invoice totals grouped by status for a tenant."""
        stmt = (
            select(
                Invoice.status,
                func.count().label("count"),
                func.coalesce(func.sum(Invoice.total_amount), 0).label("total"),
            )
            .where(Invoice.tenant_id == tenant_id)
            .group_by(Invoice.status)
        )
        result = await self.session.execute(stmt)
        return {row.status: {"count": row.count, "total": float(row.total)} for row in result.all()}

    async def get_next_invoice_number(self, tenant_id: uuid.UUID) -> str:
        """Generate a sequential invoice number scoped to a tenant."""
        stmt = select(func.count()).select_from(Invoice).where(Invoice.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        count = result.scalar_one()
        return f"INV-{str(tenant_id)[:8].upper()}-{count + 1:06d}"


class PaymentRepository(BaseRepository[Payment, PaymentCreate, dict]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Payment, session)

    async def list_by_invoice(self, invoice_id: uuid.UUID) -> list[Payment]:
        stmt = (
            select(Payment)
            .where(Payment.invoice_id == invoice_id)
            .order_by(Payment.paid_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class PayrollRepository(BaseRepository[PayrollRecord, PayrollCreate, dict]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(PayrollRecord, session)

    async def list_by_teacher(
        self, teacher_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> list[PayrollRecord]:
        stmt = (
            select(PayrollRecord)
            .where(
                PayrollRecord.teacher_id == teacher_id,
                PayrollRecord.tenant_id == tenant_id,
            )
            .order_by(PayrollRecord.period_year.desc(), PayrollRecord.period_month.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
