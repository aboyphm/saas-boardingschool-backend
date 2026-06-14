from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_active_user, require_roles
from app.core.database import AsyncSession, get_db
from app.domains.users.repository import UserRepository
from app.domains.users.schemas import UserCreate, UserResponse, UserUpdate
from app.domains.users.service import UserService
from app.shared.base_schema import PaginatedResponse
from app.shared.enums import UserRole
from app.shared.pagination import PaginationParams, get_pagination_params

router = APIRouter()


def _get_service(db: AsyncSession) -> UserService:
    return UserService(UserRepository(db))


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    current_user: Annotated[object, Depends(require_roles(
        UserRole.SUPER_ADMIN, UserRole.ADMIN_APPS, UserRole.TENANT_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = None,
) -> PaginatedResponse[UserResponse]:
    from app.domains.users.models import User as UserModel
    actor: UserModel = current_user  # type: ignore[assignment]
    tenant_id = actor.tenant_id if actor.role == UserRole.TENANT_ADMIN else None
    service = _get_service(db)
    items, total = await service.list_users(pagination, tenant_id=tenant_id, search=search)
    return PaginatedResponse.create(
        items=[UserResponse.model_validate(u) for u in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    current_user: Annotated[object, Depends(require_roles(
        UserRole.SUPER_ADMIN, UserRole.ADMIN_APPS, UserRole.TENANT_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    service = _get_service(db)
    user = await service.create_user(data)
    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    current_user: Annotated[object, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    service = _get_service(db)
    user = await service.get_or_404(user_id)
    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    current_user: Annotated[object, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    service = _get_service(db)
    user = await service.update_user(user_id, data)
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def deactivate_user(
    user_id: uuid.UUID,
    current_user: Annotated[object, Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _get_service(db)
    await service.deactivate(user_id)
    return {"ok": True}
