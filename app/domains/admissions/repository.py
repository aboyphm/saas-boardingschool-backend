from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.admissions.models import Admission, AdmissionBatch
from app.domains.admissions.schemas import (
    AdmissionBatchCreate, AdmissionBatchUpdate,
    AdmissionCreate, ReviewRequest,
)
from app.shared.base_repository import BaseRepository
from app.shared.enums import AdmissionStatus


class AdmissionBatchRepository(
    BaseRepository[AdmissionBatch, AdmissionBatchCreate, AdmissionBatchUpdate]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AdmissionBatch, session)

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[AdmissionBatch]:
        stmt = (
            select(AdmissionBatch)
            .where(AdmissionBatch.tenant_id == tenant_id)
            .order_by(AdmissionBatch.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_tenant(
        self, batch_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> AdmissionBatch | None:
        stmt = select(AdmissionBatch).where(
            AdmissionBatch.id == batch_id,
            AdmissionBatch.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class AdmissionRepository(
    BaseRepository[Admission, AdmissionCreate, ReviewRequest]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Admission, session)

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        batch_id: uuid.UUID | None = None,
        status: AdmissionStatus | None = None,
    ) -> list[Admission]:
        stmt = (
            select(Admission)
            .where(Admission.tenant_id == tenant_id)
            .order_by(Admission.created_at.desc())
        )
        if batch_id:
            stmt = stmt.where(Admission.batch_id == batch_id)
        if status:
            stmt = stmt.where(Admission.status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_tenant(
        self, admission_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Admission | None:
        stmt = select(Admission).where(
            Admission.id == admission_id,
            Admission.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_by_status(
        self, tenant_id: uuid.UUID, batch_id: uuid.UUID | None = None
    ) -> dict[str, int]:
        stmt = (
            select(Admission.status, func.count().label("cnt"))
            .where(Admission.tenant_id == tenant_id)
            .group_by(Admission.status)
        )
        if batch_id:
            stmt = stmt.where(Admission.batch_id == batch_id)
        result = await self.session.execute(stmt)
        rows = result.all()
        return {str(r.status): r.cnt for r in rows}
