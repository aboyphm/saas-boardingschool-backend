from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.tenants.models import Tenant, TenantBranding
from app.domains.tenants.schemas import TenantCreate, TenantUpdate
from app.shared.base_repository import BaseRepository


class TenantRepository(BaseRepository[Tenant, TenantCreate, TenantUpdate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Tenant, session)

    async def get_by_slug(self, slug: str) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_subdomain(self, subdomain: str) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.subdomain == subdomain)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_custom_domain(self, domain: str) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.custom_domain == domain)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_branding(self, tenant_id: uuid.UUID) -> TenantBranding | None:
        stmt = select(TenantBranding).where(TenantBranding.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_branding(
        self, tenant_id: uuid.UUID, data: dict
    ) -> TenantBranding:
        branding = await self.get_branding(tenant_id)
        if branding is None:
            branding = TenantBranding(tenant_id=tenant_id, **data)
            self.session.add(branding)
        else:
            for key, value in data.items():
                if value is not None:
                    setattr(branding, key, value)
            self.session.add(branding)
        await self.session.flush()
        await self.session.refresh(branding)
        return branding
