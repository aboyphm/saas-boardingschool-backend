"""Tests for ADMIN_APPS role tenant scoping via get_tenant_user()."""
from __future__ import annotations

import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.core.security import create_access_token, get_password_hash
from app.domains.tenants.models import Tenant
from app.domains.users.models import AdminAppsTenant, User
from app.shared.enums import SubscriptionPlan, TenantStatus, UserRole


@pytest_asyncio.fixture
async def admin_apps_user(db_session) -> User:
    """Platform-level ADMIN_APPS user (no tenant_id)."""
    user = User(
        id=uuid.uuid4(),
        tenant_id=None,
        email="admin_apps@platform.com",
        full_name="Apps Admin",
        role=UserRole.ADMIN_APPS,
        is_active=True,
        is_verified=True,
        password_hash=get_password_hash("TestPassword123"),
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def second_tenant(db_session) -> Tenant:
    """A second tenant NOT assigned to the admin_apps_user."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Other Pesantren",
        slug="other-pesantren",
        subdomain="other",
        status=TenantStatus.ACTIVE,
        plan=SubscriptionPlan.FREE,
    )
    db_session.add(tenant)
    await db_session.flush()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def admin_apps_token(admin_apps_user: User) -> str:
    return create_access_token({
        "sub": str(admin_apps_user.id),
        "tenant_id": None,
        "role": UserRole.ADMIN_APPS.value,
    })


@pytest.mark.asyncio
async def test_admin_apps_denied_without_tenant_header(
    client: AsyncClient, admin_apps_user: User, test_tenant: Tenant, admin_apps_token: str
) -> None:
    """ADMIN_APPS with no X-Tenant-ID header gets 404 (no tenant resolved)."""
    response = await client.get(
        "/api/v1/students/",
        headers={"Authorization": f"Bearer {admin_apps_token}"},
    )
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_admin_apps_denied_for_unassigned_tenant(
    client: AsyncClient,
    admin_apps_user: User,
    second_tenant: Tenant,
    admin_apps_token: str,
) -> None:
    """ADMIN_APPS gets 403 when accessing a tenant they are not assigned to."""
    response = await client.get(
        "/api/v1/students/",
        headers={
            "Authorization": f"Bearer {admin_apps_token}",
            "X-Tenant-ID": str(second_tenant.id),
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_apps_allowed_for_assigned_tenant(
    client: AsyncClient,
    db_session,
    admin_apps_user: User,
    test_tenant: Tenant,
    admin_apps_token: str,
) -> None:
    """ADMIN_APPS can access a tenant they are assigned to."""
    assignment = AdminAppsTenant(
        admin_apps_user_id=admin_apps_user.id,
        tenant_id=test_tenant.id,
        created_by=admin_apps_user.id,
    )
    db_session.add(assignment)
    await db_session.flush()

    response = await client.get(
        "/api/v1/students/",
        headers={
            "Authorization": f"Bearer {admin_apps_token}",
            "X-Tenant-ID": str(test_tenant.id),
        },
    )
    assert response.status_code == 200


# ─── Service tests ────────────────────────────────────────────────────────────

from app.domains.admin_apps.repository import AdminAppsRepository
from app.domains.admin_apps.schemas import AdminAppsUserCreate
from app.domains.admin_apps.service import AdminAppsService
from app.domains.tenants.repository import TenantRepository
from app.domains.users.repository import UserRepository
from app.core.exceptions import ConflictError, NotFoundError


def _make_service(db_session):
    return AdminAppsService(
        admin_apps_repo=AdminAppsRepository(db_session),
        user_repo=UserRepository(db_session),
        tenant_repo=TenantRepository(db_session),
    )


@pytest.mark.asyncio
async def test_create_admin_apps_user(db_session, test_tenant) -> None:
    """Service creates a user with ADMIN_APPS role and no tenant_id."""
    super_admin = User(
        id=uuid.uuid4(),
        tenant_id=None,
        email="sa@platform.com",
        full_name="Super Admin",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
        is_verified=True,
        password_hash=get_password_hash("Password123"),
    )
    db_session.add(super_admin)
    await db_session.flush()

    svc = _make_service(db_session)
    user = await svc.create_admin_apps_user(
        AdminAppsUserCreate(
            full_name="New Apps Admin",
            email="new_apps@platform.com",
            password="SecurePass123",
        ),
    )
    assert user.role == UserRole.ADMIN_APPS
    assert user.tenant_id is None


@pytest.mark.asyncio
async def test_assign_tenant(db_session, admin_apps_user, test_tenant) -> None:
    """Service assigns a tenant to an ADMIN_APPS user."""
    svc = _make_service(db_session)
    assignment = await svc.assign_tenant(
        admin_user_id=admin_apps_user.id,
        tenant_id=test_tenant.id,
        created_by=admin_apps_user.id,
    )
    assert assignment.id == test_tenant.id


@pytest.mark.asyncio
async def test_assign_tenant_duplicate_raises_conflict(
    db_session, admin_apps_user, test_tenant
) -> None:
    """Assigning the same tenant twice raises ConflictError."""
    svc = _make_service(db_session)
    await svc.assign_tenant(admin_apps_user.id, test_tenant.id, admin_apps_user.id)
    with pytest.raises(ConflictError):
        await svc.assign_tenant(admin_apps_user.id, test_tenant.id, admin_apps_user.id)


@pytest.mark.asyncio
async def test_remove_tenant(db_session, admin_apps_user, test_tenant) -> None:
    """Service removes a tenant assignment."""
    svc = _make_service(db_session)
    await svc.assign_tenant(admin_apps_user.id, test_tenant.id, admin_apps_user.id)
    await svc.remove_tenant(admin_apps_user.id, test_tenant.id)
    has_access = await AdminAppsRepository(db_session).has_access(
        admin_apps_user.id, test_tenant.id
    )
    assert has_access is False


@pytest.mark.asyncio
async def test_list_my_tenants(db_session, admin_apps_user, test_tenant) -> None:
    """list_my_tenants returns only tenants assigned to the user."""
    svc = _make_service(db_session)
    await svc.assign_tenant(admin_apps_user.id, test_tenant.id, admin_apps_user.id)
    tenants = await svc.list_my_tenants(admin_apps_user.id)
    assert len(tenants) == 1
    assert tenants[0].tenant_id == test_tenant.id


# ─── Endpoint integration tests ───────────────────────────────────────────────

from app.core.security import create_access_token as _cat


@pytest.mark.asyncio
async def test_list_admin_apps_users_requires_super_admin(
    client: AsyncClient, admin_apps_user: User, admin_apps_token: str
) -> None:
    """GET /admin-apps/ returns 403 for non-SUPER_ADMIN callers."""
    response = await client.get(
        "/api/v1/admin-apps/",
        headers={"Authorization": f"Bearer {admin_apps_token}"},
    )
    assert response.status_code == 403


@pytest_asyncio.fixture
async def super_admin_user(db_session) -> User:
    """Platform-level SUPER_ADMIN user (no tenant_id)."""
    user = User(
        id=uuid.uuid4(),
        tenant_id=None,
        email="superadmin@platform.com",
        full_name="Super Admin",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
        is_verified=True,
        password_hash=get_password_hash("TestPassword123"),
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def super_admin_token(super_admin_user: User) -> str:
    return _cat({
        "sub": str(super_admin_user.id),
        "tenant_id": None,
        "role": UserRole.SUPER_ADMIN.value,
    })


@pytest.mark.asyncio
async def test_super_admin_can_list_admin_apps_users(
    client: AsyncClient, admin_apps_user: User, super_admin_token: str
) -> None:
    """SUPER_ADMIN gets a list of all ADMIN_APPS users."""
    response = await client.get(
        "/api/v1/admin-apps/",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_super_admin_can_assign_and_remove_tenant(
    client: AsyncClient,
    db_session,
    admin_apps_user: User,
    test_tenant: Tenant,
) -> None:
    """SUPER_ADMIN can assign then remove a tenant for an ADMIN_APPS user."""
    sa_user = User(
        id=uuid.uuid4(),
        tenant_id=None,
        email="sa2@platform.com",
        full_name="Super Admin 2",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
        is_verified=True,
        password_hash=get_password_hash("Password123"),
    )
    db_session.add(sa_user)
    await db_session.flush()

    sa_token = _cat({"sub": str(sa_user.id), "tenant_id": None, "role": "super_admin"})

    # Assign
    resp = await client.post(
        f"/api/v1/admin-apps/{admin_apps_user.id}/tenants",
        json={"tenant_id": str(test_tenant.id)},
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert resp.status_code == 201

    # Remove
    resp = await client.delete(
        f"/api/v1/admin-apps/{admin_apps_user.id}/tenants/{test_tenant.id}",
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_admin_apps_can_get_my_tenants(
    client: AsyncClient,
    db_session,
    admin_apps_user: User,
    test_tenant: Tenant,
) -> None:
    """ADMIN_APPS user can list their own assigned tenants."""
    assignment = AdminAppsTenant(
        admin_apps_user_id=admin_apps_user.id,
        tenant_id=test_tenant.id,
        created_by=admin_apps_user.id,
    )
    db_session.add(assignment)
    await db_session.flush()

    token = _cat({"sub": str(admin_apps_user.id), "tenant_id": None, "role": "admin_apps"})
    response = await client.get(
        "/api/v1/admin-apps/me/tenants",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["tenant_id"] == str(test_tenant.id)


@pytest.mark.asyncio
async def test_admin_apps_auto_assigned_on_tenant_create(
    client: AsyncClient,
    db_session,
    admin_apps_user: User,
) -> None:
    """When ADMIN_APPS creates a tenant, they are auto-assigned to it."""
    token = _cat({"sub": str(admin_apps_user.id), "tenant_id": None, "role": "admin_apps"})
    response = await client.post(
        "/api/v1/tenants/",
        json={
            "name": "Auto Assign Test",
            "slug": "auto-assign-test",
            "subdomain": "autotest",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    new_tenant_id = uuid.UUID(response.json()["id"])

    has_access = await AdminAppsRepository(db_session).has_access(
        admin_apps_user.id, new_tenant_id
    )
    assert has_access is True
