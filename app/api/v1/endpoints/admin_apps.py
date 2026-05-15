from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_current_active_user, require_roles
from app.core.database import AsyncSession, get_db
from app.domains.admin_apps.repository import AdminAppsRepository
from app.domains.admin_apps.schemas import (
    AdminAppsTenantAssign,
    AdminAppsUserCreate,
    AdminAppsUserResponse,
    TenantBrief,
)
from app.domains.admin_apps.service import AdminAppsService
from app.domains.tenants.repository import TenantRepository
from app.domains.users.models import User
from app.domains.users.repository import UserRepository
from app.shared.enums import UserRole

router = APIRouter()


def _get_service(db: AsyncSession) -> AdminAppsService:
    return AdminAppsService(
        admin_apps_repo=AdminAppsRepository(db),
        user_repo=UserRepository(db),
        tenant_repo=TenantRepository(db),
    )


@router.get(
    "/",
    response_model=list[AdminAppsUserResponse],
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN))],
)
async def list_admin_apps_users(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AdminAppsUserResponse]:
    return await _get_service(db).list_admin_apps_users()


@router.post(
    "/",
    response_model=AdminAppsUserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN))],
)
async def create_admin_apps_user(
    data: AdminAppsUserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminAppsUserResponse:
    user = await _get_service(db).create_admin_apps_user(data)
    return AdminAppsUserResponse(
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        assigned_tenants=[],
    )


@router.get(
    "/me/tenants",
    response_model=list[TenantBrief],
    dependencies=[Depends(require_roles(UserRole.ADMIN_APPS))],
)
async def get_my_tenants(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TenantBrief]:
    return await _get_service(db).list_my_tenants(current_user.id)


@router.post(
    "/{user_id}/tenants",
    response_model=TenantBrief,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN))],
)
async def assign_tenant(
    user_id: uuid.UUID,
    data: AdminAppsTenantAssign,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TenantBrief:
    tenant = await _get_service(db).assign_tenant(user_id, data.tenant_id, current_user.id)
    return TenantBrief(tenant_id=tenant.id, name=tenant.name, subdomain=tenant.subdomain)


@router.delete(
    "/{user_id}/tenants/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN))],
)
async def remove_tenant(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    await _get_service(db).remove_tenant(user_id, tenant_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
