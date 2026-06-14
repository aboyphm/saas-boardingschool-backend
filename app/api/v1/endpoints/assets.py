from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_active_user, require_roles
from app.core.database import AsyncSession, get_db
from app.core.exceptions import ForbiddenError
from app.domains.assets.repository import AssetRepository
from app.domains.assets.schemas import (
    AssetCreate, AssetResponse, AssetStatsResponse, AssetUpdate,
)
from app.domains.assets.service import AssetService
from app.domains.users.models import User
from app.shared.enums import AssetCategory, AssetCondition, UserRole

router = APIRouter()

WRITE_ROLES = (UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN)


def _tid(user: User) -> uuid.UUID:
    if user.tenant_id is None:
        raise ForbiddenError("A tenant context is required.")
    return user.tenant_id


def _get_service(db: AsyncSession) -> AssetService:
    return AssetService(repo=AssetRepository(db))


@router.get("", response_model=list[AssetResponse])
async def list_assets(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: AssetCategory | None = Query(default=None),
    condition: AssetCondition | None = Query(default=None),
    search: str | None = Query(default=None),
) -> list[AssetResponse]:
    service = _get_service(db)
    assets = await service.list_assets(_tid(current_user), category, condition, search)
    return [AssetResponse.model_validate(a) for a in assets]


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    data: AssetCreate,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AssetResponse:
    service = _get_service(db)
    asset = await service.create_asset(data, _tid(current_user))
    return AssetResponse.model_validate(asset)


@router.get("/stats", response_model=AssetStatsResponse)
async def get_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AssetStatsResponse:
    service = _get_service(db)
    return await service.get_stats(_tid(current_user))


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AssetResponse:
    service = _get_service(db)
    asset = await service.get_asset_or_404(asset_id, _tid(current_user))
    return AssetResponse.model_validate(asset)


@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: uuid.UUID,
    data: AssetUpdate,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AssetResponse:
    service = _get_service(db)
    asset = await service.update_asset(asset_id, data, _tid(current_user))
    return AssetResponse.model_validate(asset)


@router.delete("/{asset_id}", status_code=status.HTTP_200_OK)
async def delete_asset(
    asset_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _get_service(db)
    await service.delete_asset(asset_id, _tid(current_user))
    return {"ok": True}
