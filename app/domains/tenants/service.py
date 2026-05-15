from __future__ import annotations

import uuid

from app.core.exceptions import ConflictError, NotFoundError, TenantNotFoundError
from app.domains.tenants.models import Tenant, TenantBranding
from app.domains.tenants.repository import TenantRepository
from app.domains.tenants.schemas import (
    TenantBrandingUpdate,
    TenantCreate,
    TenantStatsResponse,
    TenantUpdate,
)
from app.shared.enums import TenantStatus


class TenantService:
    def __init__(self, repository: TenantRepository) -> None:
        self.repository = repository

    async def create_tenant(self, data: TenantCreate) -> Tenant:
        """Create a new tenant, enforcing slug and subdomain uniqueness."""
        if await self.repository.exists({"slug": data.slug}):
            raise ConflictError(f"Slug '{data.slug}' is already taken.")
        if await self.repository.exists({"subdomain": data.subdomain}):
            raise ConflictError(f"Subdomain '{data.subdomain}' is already taken.")
        return await self.repository.create(data)

    async def get_or_404(self, tenant_id: uuid.UUID) -> Tenant:
        tenant = await self.repository.get(tenant_id)
        if tenant is None:
            raise TenantNotFoundError()
        return tenant

    async def update_tenant(
        self, tenant_id: uuid.UUID, data: TenantUpdate
    ) -> Tenant:
        tenant = await self.get_or_404(tenant_id)
        updated = await self.repository.update(tenant.id, data)
        if updated is None:
            raise TenantNotFoundError()
        return updated

    async def suspend(self, tenant_id: uuid.UUID) -> Tenant:
        tenant = await self.get_or_404(tenant_id)
        tenant.status = TenantStatus.SUSPENDED
        self.repository.session.add(tenant)
        await self.repository.session.flush()
        await self.repository.session.refresh(tenant)
        return tenant

    async def activate(self, tenant_id: uuid.UUID) -> Tenant:
        tenant = await self.get_or_404(tenant_id)
        tenant.status = TenantStatus.ACTIVE
        self.repository.session.add(tenant)
        await self.repository.session.flush()
        await self.repository.session.refresh(tenant)
        return tenant

    async def get_stats(self, tenant_id: uuid.UUID) -> TenantStatsResponse:
        """Aggregate tenant statistics. Counts are retrieved via individual queries."""
        tenant = await self.get_or_404(tenant_id)

        from sqlalchemy import func, select

        session = self.repository.session

        from app.domains.students.models import Student
        from app.domains.teachers.models import Teacher
        from app.domains.users.models import User
        from app.domains.finance.models import Invoice
        from app.shared.enums import StudentStatus, InvoiceStatus

        student_count_result = await session.execute(
            select(func.count()).select_from(Student).where(
                Student.tenant_id == tenant_id,
                Student.is_deleted.is_(False),
                Student.status == StudentStatus.ACTIVE,
            )
        )
        teacher_count_result = await session.execute(
            select(func.count()).select_from(Teacher).where(
                Teacher.tenant_id == tenant_id,
                Teacher.is_deleted.is_(False),
            )
        )
        user_count_result = await session.execute(
            select(func.count()).select_from(User).where(
                User.tenant_id == tenant_id,
                User.is_active.is_(True),
                User.is_deleted.is_(False),
            )
        )
        invoice_count_result = await session.execute(
            select(func.count()).select_from(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.status == InvoiceStatus.OVERDUE,
            )
        )

        return TenantStatsResponse(
            tenant_id=tenant_id,
            total_students=student_count_result.scalar_one(),
            total_teachers=teacher_count_result.scalar_one(),
            total_active_users=user_count_result.scalar_one(),
            storage_used_gb=tenant.storage_used_gb,
            storage_limit_gb=tenant.max_storage_gb,
            outstanding_invoices=invoice_count_result.scalar_one(),
            total_revenue_month=0.0,  # Placeholder — aggregate in finance service
        )

    async def update_branding(
        self, tenant_id: uuid.UUID, data: TenantBrandingUpdate
    ) -> TenantBranding:
        await self.get_or_404(tenant_id)
        return await self.repository.upsert_branding(
            tenant_id,
            data.model_dump(exclude_none=True),
        )
