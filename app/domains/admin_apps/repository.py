from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.users.models import AdminAppsTenant


# Association-table repo: no full CRUD entity, so we skip BaseRepository inheritance.
class AdminAppsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def assign_tenant(
        self,
        admin_user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        created_by: uuid.UUID,
    ) -> AdminAppsTenant:
        row = AdminAppsTenant(
            admin_apps_user_id=admin_user_id,
            tenant_id=tenant_id,
            created_by=created_by,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def remove_tenant(
        self, admin_user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> bool:
        stmt = select(AdminAppsTenant).where(
            AdminAppsTenant.admin_apps_user_id == admin_user_id,
            AdminAppsTenant.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True

    async def get_assigned_tenants(
        self, admin_user_id: uuid.UUID
    ) -> list[AdminAppsTenant]:
        stmt = select(AdminAppsTenant).where(
            AdminAppsTenant.admin_apps_user_id == admin_user_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def has_access(
        self, admin_user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> bool:
        stmt = select(AdminAppsTenant).where(
            AdminAppsTenant.admin_apps_user_id == admin_user_id,
            AdminAppsTenant.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_tenants_for_admin(self, admin_user_id: uuid.UUID) -> list:
        from app.domains.tenants.models import Tenant
        stmt = (
            select(Tenant)
            .join(AdminAppsTenant, AdminAppsTenant.tenant_id == Tenant.id)
            .where(AdminAppsTenant.admin_apps_user_id == admin_user_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_tenants_for_admins_batch(
        self, admin_user_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list]:
        """Returns {admin_user_id: [Tenant, ...]} for all given user IDs in one query."""
        if not admin_user_ids:
            return {}
        from app.domains.tenants.models import Tenant
        stmt = (
            select(AdminAppsTenant.admin_apps_user_id, Tenant)
            .join(Tenant, AdminAppsTenant.tenant_id == Tenant.id)
            .where(AdminAppsTenant.admin_apps_user_id.in_(admin_user_ids))
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        grouped: dict[uuid.UUID, list] = {uid: [] for uid in admin_user_ids}
        for admin_user_id, tenant in rows:
            grouped[admin_user_id].append(tenant)
        return grouped
