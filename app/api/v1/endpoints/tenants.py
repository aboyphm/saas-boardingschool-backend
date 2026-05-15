from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_active_user, require_roles
from app.core.database import AsyncSession, get_db
from app.domains.tenants.repository import TenantRepository
from app.domains.users.models import User
from app.domains.tenants.schemas import (
    TenantBrandingUpdate,
    TenantCreate,
    TenantResponse,
    TenantStatsResponse,
    TenantUpdate,
)
from app.domains.admin_apps.repository import AdminAppsRepository
from app.domains.tenants.service import TenantService
from app.shared.base_schema import PaginatedResponse
from app.shared.enums import UserRole
from app.shared.pagination import PaginationParams, get_pagination_params

router = APIRouter()


def _get_service(db: AsyncSession) -> TenantService:
    return TenantService(TenantRepository(db))


@router.get(
    "/",
    response_model=PaginatedResponse[TenantResponse],
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN))],
)
async def list_tenants(
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaginatedResponse[TenantResponse]:
    service = _get_service(db)
    items, total = await service.repository.list(
        skip=pagination.offset, limit=pagination.size
    ), await service.repository.count()
    return PaginatedResponse.create(
        items=[TenantResponse.model_validate(t) for t in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


@router.post(
    "/",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tenant(
    data: TenantCreate,
    current_user: Annotated[User, Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN_APPS))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TenantResponse:
    service = _get_service(db)
    tenant = await service.create_tenant(data)
    if current_user.role == UserRole.ADMIN_APPS:
        await AdminAppsRepository(db).assign_tenant(
            current_user.id, tenant.id, current_user.id
        )
    return TenantResponse.model_validate(tenant)


@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN))],
)
async def get_tenant(
    tenant_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TenantResponse:
    service = _get_service(db)
    tenant = await service.get_or_404(tenant_id)
    return TenantResponse.model_validate(tenant)


@router.put(
    "/{tenant_id}",
    response_model=TenantResponse,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN))],
)
async def update_tenant(
    tenant_id: uuid.UUID,
    data: TenantUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TenantResponse:
    service = _get_service(db)
    tenant = await service.update_tenant(tenant_id, data)
    return TenantResponse.model_validate(tenant)


@router.post(
    "/{tenant_id}/suspend",
    response_model=TenantResponse,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN))],
)
async def suspend_tenant(
    tenant_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TenantResponse:
    service = _get_service(db)
    tenant = await service.suspend(tenant_id)
    return TenantResponse.model_validate(tenant)


@router.post(
    "/{tenant_id}/activate",
    response_model=TenantResponse,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN))],
)
async def activate_tenant(
    tenant_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TenantResponse:
    service = _get_service(db)
    tenant = await service.activate(tenant_id)
    return TenantResponse.model_validate(tenant)


@router.get(
    "/{tenant_id}/stats",
    response_model=TenantStatsResponse,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.OWNER, UserRole.TENANT_ADMIN))],
)
async def get_tenant_stats(
    tenant_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TenantStatsResponse:
    service = _get_service(db)
    return await service.get_stats(tenant_id)


@router.put(
    "/{tenant_id}/branding",
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN))],
)
async def update_branding(
    tenant_id: uuid.UUID,
    data: TenantBrandingUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _get_service(db)
    branding = await service.update_branding(tenant_id, data)
    return {"id": str(branding.id), "tenant_id": str(branding.tenant_id)}
