from __future__ import annotations

import uuid

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import get_password_hash
from app.domains.admin_apps.repository import AdminAppsRepository
from app.domains.admin_apps.schemas import (
    AdminAppsUserCreate,
    AdminAppsUserResponse,
    TenantBrief,
)
from app.domains.tenants.models import Tenant
from app.domains.tenants.repository import TenantRepository
from app.domains.users.models import User
from app.domains.users.repository import UserRepository
from app.shared.enums import UserRole


class AdminAppsService:
    def __init__(
        self,
        admin_apps_repo: AdminAppsRepository,
        user_repo: UserRepository,
        tenant_repo: TenantRepository,
    ) -> None:
        self.admin_apps_repo = admin_apps_repo
        self.user_repo = user_repo
        self.tenant_repo = tenant_repo

    async def create_admin_apps_user(
        self, data: AdminAppsUserCreate
    ) -> User:
        existing = await self.user_repo.get_by_email(data.email)
        if existing is not None:
            raise ConflictError("Email already in use.")
        user = User(
            email=data.email,
            full_name=data.full_name,
            role=UserRole.ADMIN_APPS,
            tenant_id=None,
            is_active=True,
            is_verified=True,
            password_hash=get_password_hash(data.password),
        )
        return await self.user_repo.save(user)

    async def assign_tenant(
        self,
        admin_user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        created_by: uuid.UUID,
    ) -> Tenant:
        user = await self.user_repo.get(admin_user_id)
        if user is None or user.role != UserRole.ADMIN_APPS:
            raise NotFoundError("ADMIN_APPS user not found.")
        tenant = await self.tenant_repo.get(tenant_id)
        if tenant is None:
            raise NotFoundError("Tenant not found.")
        if await self.admin_apps_repo.has_access(admin_user_id, tenant_id):
            raise ConflictError("Tenant already assigned to this user.")
        await self.admin_apps_repo.assign_tenant(admin_user_id, tenant_id, created_by)
        return tenant

    async def remove_tenant(
        self, admin_user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        removed = await self.admin_apps_repo.remove_tenant(admin_user_id, tenant_id)
        if not removed:
            raise NotFoundError("Assignment not found.")

    async def list_admin_apps_users(self) -> list[AdminAppsUserResponse]:
        users = await self.user_repo.list(filters={"role": UserRole.ADMIN_APPS}, limit=1000)
        user_ids = [u.id for u in users]
        tenant_map = await self.admin_apps_repo.get_tenants_for_admins_batch(user_ids)
        return [
            AdminAppsUserResponse(
                user_id=u.id,
                full_name=u.full_name,
                email=u.email,
                assigned_tenants=[
                    TenantBrief(tenant_id=t.id, name=t.name, subdomain=t.subdomain)
                    for t in tenant_map.get(u.id, [])
                ],
            )
            for u in users
        ]

    async def list_my_tenants(self, admin_user_id: uuid.UUID) -> list[TenantBrief]:
        tenants = await self.admin_apps_repo.get_tenants_for_admin(admin_user_id)
        return [
            TenantBrief(tenant_id=t.id, name=t.name, subdomain=t.subdomain)
            for t in tenants
        ]
