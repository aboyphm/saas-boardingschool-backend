from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_active_user, require_roles
from app.core.database import AsyncSession, get_db
from app.domains.subscriptions.repository import SubscriptionPackageRepository
from app.domains.subscriptions.schemas import (
    SubscriptionPackageCreate,
    SubscriptionPackageResponse,
    SubscriptionPackageUpdate,
)
from app.domains.subscriptions.service import SubscriptionService
from app.domains.users.models import User
from app.shared.enums import UserRole

router = APIRouter()

READ_ROLES = (UserRole.SUPER_ADMIN, UserRole.ADMIN_APPS)
WRITE_ROLES = (UserRole.SUPER_ADMIN,)


def _get_service(db: AsyncSession) -> SubscriptionService:
    return SubscriptionService(repo=SubscriptionPackageRepository(db))


@router.get("/packages", response_model=list[SubscriptionPackageResponse])
async def list_packages(
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SubscriptionPackageResponse]:
    service = _get_service(db)
    packages = await service.list_packages()
    return [SubscriptionPackageResponse.model_validate(p) for p in packages]


@router.post("/packages", response_model=SubscriptionPackageResponse, status_code=status.HTTP_201_CREATED)
async def create_package(
    data: SubscriptionPackageCreate,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SubscriptionPackageResponse:
    service = _get_service(db)
    pkg = await service.create_package(data)
    return SubscriptionPackageResponse.model_validate(pkg)


@router.put("/packages/{package_id}", response_model=SubscriptionPackageResponse)
async def update_package(
    package_id: uuid.UUID,
    data: SubscriptionPackageUpdate,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SubscriptionPackageResponse:
    service = _get_service(db)
    pkg = await service.update_package(package_id, data)
    return SubscriptionPackageResponse.model_validate(pkg)


@router.delete("/packages/{package_id}", status_code=status.HTTP_200_OK)
async def delete_package(
    package_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _get_service(db)
    await service.delete_package(package_id)
    return {"ok": True}
