from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.exceptions import ConflictError, NotFoundError
from app.domains.admissions.models import Admission, AdmissionBatch
from app.domains.admissions.repository import AdmissionBatchRepository, AdmissionRepository
from app.domains.admissions.schemas import (
    AdmissionBatchCreate, AdmissionBatchUpdate,
    AdmissionCreate, AdmissionStatsResponse, ReviewRequest,
)
from app.shared.enums import AdmissionStatus


class AdmissionService:
    def __init__(
        self,
        batch_repo: AdmissionBatchRepository,
        admission_repo: AdmissionRepository,
    ) -> None:
        self.batch_repo = batch_repo
        self.admission_repo = admission_repo

    # ── Batches ───────────────────────────────────────────────────────────────
    async def list_batches(self, tenant_id: uuid.UUID) -> list[AdmissionBatch]:
        return await self.batch_repo.list_by_tenant(tenant_id)

    async def get_batch_or_404(
        self, batch_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> AdmissionBatch:
        batch = await self.batch_repo.get_by_tenant(batch_id, tenant_id)
        if batch is None:
            raise NotFoundError("Admission batch not found.")
        return batch

    async def create_batch(
        self, data: AdmissionBatchCreate, tenant_id: uuid.UUID
    ) -> AdmissionBatch:
        batch = AdmissionBatch(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
            open_date=data.open_date,
            close_date=data.close_date,
            quota=data.quota,
            status=data.status,
            is_active=data.is_active,
        )
        self.batch_repo.session.add(batch)
        await self.batch_repo.session.flush()
        await self.batch_repo.session.refresh(batch)
        return batch

    async def update_batch(
        self, batch_id: uuid.UUID, data: AdmissionBatchUpdate, tenant_id: uuid.UUID
    ) -> AdmissionBatch:
        batch = await self.get_batch_or_404(batch_id, tenant_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(batch, field, value)
        await self.batch_repo.session.flush()
        await self.batch_repo.session.refresh(batch)
        return batch

    async def delete_batch(self, batch_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        batch = await self.get_batch_or_404(batch_id, tenant_id)
        await self.batch_repo.session.delete(batch)
        await self.batch_repo.session.flush()

    # ── Applications ─────────────────────────────────────────────────────────
    async def list_applications(
        self,
        tenant_id: uuid.UUID,
        batch_id: uuid.UUID | None = None,
        status: AdmissionStatus | None = None,
    ) -> list[Admission]:
        return await self.admission_repo.list_by_tenant(tenant_id, batch_id, status)

    async def get_application_or_404(
        self, admission_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Admission:
        app = await self.admission_repo.get_by_tenant(admission_id, tenant_id)
        if app is None:
            raise NotFoundError("Admission not found.")
        return app

    async def create_application(
        self, data: AdmissionCreate, tenant_id: uuid.UUID
    ) -> Admission:
        # Verify batch exists and is open
        batch = await self.batch_repo.get_by_tenant(data.batch_id, tenant_id)
        if batch is None:
            raise NotFoundError("Admission batch not found.")
        if not batch.is_active:
            raise ConflictError("This admission batch is not currently accepting applications.")
        admission = Admission(
            tenant_id=tenant_id,
            batch_id=data.batch_id,
            applicant_name=data.applicant_name,
            parent_name=data.parent_name,
            phone=data.phone,
            email=data.email,
            birth_date=data.birth_date,
            origin_school=data.origin_school,
            notes=data.notes,
            status=AdmissionStatus.SUBMITTED,
        )
        self.admission_repo.session.add(admission)
        await self.admission_repo.session.flush()
        await self.admission_repo.session.refresh(admission)
        return admission

    async def review_application(
        self,
        admission_id: uuid.UUID,
        data: ReviewRequest,
        reviewer_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Admission:
        app = await self.get_application_or_404(admission_id, tenant_id)
        app.status = data.status
        app.reviewed_by = reviewer_id
        app.reviewed_at = datetime.now(timezone.utc)
        if data.status == AdmissionStatus.REJECTED:
            app.rejection_reason = data.rejection_reason
        await self.admission_repo.session.flush()
        await self.admission_repo.session.refresh(app)
        return app

    async def get_stats(
        self, tenant_id: uuid.UUID, batch_id: uuid.UUID | None = None
    ) -> AdmissionStatsResponse:
        counts = await self.admission_repo.count_by_status(tenant_id, batch_id)
        total = sum(counts.values())
        return AdmissionStatsResponse(
            total=total,
            submitted=counts.get("submitted", 0),
            under_review=counts.get("under_review", 0),
            accepted=counts.get("accepted", 0),
            rejected=counts.get("rejected", 0),
        )
