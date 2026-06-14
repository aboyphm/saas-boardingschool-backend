from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.assets.models import Asset
from app.domains.assets.schemas import AssetCreate, AssetUpdate
from app.shared.base_repository import BaseRepository
from app.shared.enums import AssetCategory, AssetCondition


class AssetRepository(BaseRepository[Asset, AssetCreate, AssetUpdate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Asset, session)

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        category: AssetCategory | None = None,
        condition: AssetCondition | None = None,
        search: str | None = None,
    ) -> list[Asset]:
        stmt = (
            select(Asset)
            .where(Asset.tenant_id == tenant_id, Asset.is_active.is_(True))
            .order_by(Asset.created_at.desc())
        )
        if category:
            stmt = stmt.where(Asset.category == category)
        if condition:
            stmt = stmt.where(Asset.condition == condition)
        if search:
            stmt = stmt.where(Asset.name.ilike(f"%{search}%"))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_tenant(
        self, asset_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Asset | None:
        stmt = select(Asset).where(
            Asset.id == asset_id, Asset.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_by_condition(self, tenant_id: uuid.UUID) -> dict[str, int]:
        stmt = (
            select(Asset.condition, func.count().label("cnt"))
            .where(Asset.tenant_id == tenant_id, Asset.is_active.is_(True))
            .group_by(Asset.condition)
        )
        result = await self.session.execute(stmt)
        return {str(r.condition): r.cnt for r in result.all()}
