from __future__ import annotations

import uuid

from app.core.exceptions import NotFoundError
from app.domains.assets.models import Asset
from app.domains.assets.repository import AssetRepository
from app.domains.assets.schemas import (
    AssetCreate, AssetStatsResponse, AssetUpdate,
)
from app.shared.enums import AssetCategory, AssetCondition


class AssetService:
    def __init__(self, repo: AssetRepository) -> None:
        self.repo = repo

    async def list_assets(
        self,
        tenant_id: uuid.UUID,
        category: AssetCategory | None = None,
        condition: AssetCondition | None = None,
        search: str | None = None,
    ) -> list[Asset]:
        return await self.repo.list_by_tenant(tenant_id, category, condition, search)

    async def get_asset_or_404(
        self, asset_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Asset:
        asset = await self.repo.get_by_tenant(asset_id, tenant_id)
        if asset is None:
            raise NotFoundError("Asset not found.")
        return asset

    async def create_asset(
        self, data: AssetCreate, tenant_id: uuid.UUID
    ) -> Asset:
        asset = Asset(
            tenant_id=tenant_id,
            name=data.name,
            category=data.category,
            serial_number=data.serial_number,
            location=data.location,
            condition=data.condition,
            purchase_date=data.purchase_date,
            purchase_price=float(data.purchase_price) if data.purchase_price else None,
            notes=data.notes,
            is_active=data.is_active,
        )
        self.repo.session.add(asset)
        await self.repo.session.flush()
        await self.repo.session.refresh(asset)
        return asset

    async def update_asset(
        self, asset_id: uuid.UUID, data: AssetUpdate, tenant_id: uuid.UUID
    ) -> Asset:
        asset = await self.get_asset_or_404(asset_id, tenant_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(asset, field, value)
        await self.repo.session.flush()
        await self.repo.session.refresh(asset)
        return asset

    async def delete_asset(
        self, asset_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        asset = await self.get_asset_or_404(asset_id, tenant_id)
        asset.is_active = False
        await self.repo.session.flush()

    async def get_stats(self, tenant_id: uuid.UUID) -> AssetStatsResponse:
        counts = await self.repo.count_by_condition(tenant_id)
        total = sum(counts.values())
        return AssetStatsResponse(
            total=total,
            good=counts.get("good", 0),
            fair=counts.get("fair", 0),
            poor=counts.get("poor", 0),
            broken=counts.get("broken", 0),
            lost=counts.get("lost", 0),
        )
