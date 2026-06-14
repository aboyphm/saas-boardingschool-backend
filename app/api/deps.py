from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated

if TYPE_CHECKING:
    from app.domains.students.models import Student

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from app.core.database import AsyncSession, get_db
from app.core.exceptions import ForbiddenError, TenantNotFoundError, TenantSuspendedError, UnauthorizedError
from app.core.security import verify_token
from app.domains.users.models import User
from app.domains.users.repository import UserRepository
from app.shared.enums import TenantStatus, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Decode and validate the JWT access token, then load the corresponding user.

    :raises UnauthorizedError: If the token is invalid or the user does not exist.
    """
    payload = verify_token(token)
    if payload.token_type != "access":
        raise UnauthorizedError("Invalid token type. Use an access token.")

    repo = UserRepository(db)
    user = await repo.get(payload.user_id)
    if user is None:
        raise UnauthorizedError("User not found.")
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Ensure the authenticated user's account is active.

    :raises UnauthorizedError: If the account has been deactivated.
    """
    if not current_user.is_active:
        raise UnauthorizedError("Account is deactivated.")
    return current_user


async def get_tenant_user(
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Verify the authenticated user has access to the tenant resolved from the request.

    - SUPER_ADMIN: bypasses all tenant checks.
    - ADMIN_APPS: must have a row in admin_apps_tenants for the resolved tenant.
    - All other roles: user.tenant_id must match the resolved tenant.

    :raises TenantNotFoundError: If no tenant could be resolved.
    :raises ForbiddenError: If the user does not have access to this tenant.
    :raises TenantSuspendedError: If the tenant is suspended.
    """
    if current_user.role == UserRole.SUPER_ADMIN:
        return current_user

    tenant_id_str: str | None = getattr(request.state, "tenant_id", None)
    tenant_slug: str | None = getattr(request.state, "tenant_slug", None)

    from app.domains.tenants.repository import TenantRepository
    tenant_repo = TenantRepository(db)

    tenant = None
    if tenant_id_str:
        try:
            tenant = await tenant_repo.get(uuid.UUID(tenant_id_str))
        except ValueError:
            pass
    elif tenant_slug:
        tenant = await tenant_repo.get_by_slug(tenant_slug)

    if tenant is None:
        if current_user.tenant_id is None:
            raise TenantNotFoundError()
        return current_user

    if tenant.status == TenantStatus.SUSPENDED:
        raise TenantSuspendedError()

    if current_user.role == UserRole.ADMIN_APPS:
        from sqlalchemy import select
        from app.domains.users.models import AdminAppsTenant
        stmt = select(AdminAppsTenant).where(
            AdminAppsTenant.admin_apps_user_id == current_user.id,
            AdminAppsTenant.tenant_id == tenant.id,
        )
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is None:
            raise ForbiddenError("You do not have access to this tenant.")
        return current_user

    if current_user.tenant_id != tenant.id:
        raise ForbiddenError("You do not have access to this tenant.")

    return current_user


async def get_current_student(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> "Student":
    """Resolve the Student record for the currently authenticated STUDENT user.
    Raises ForbiddenError if no student record is linked to this account.
    """
    from app.domains.students.repository import StudentRepository
    repo = StudentRepository(db)
    if current_user.tenant_id is None:
        raise ForbiddenError("No student record found for this user account.")
    student = await repo.get_by_user_id(current_user.id, current_user.tenant_id)
    if student is None:
        raise ForbiddenError("No student record found for this user account.")
    return student


def require_roles(*roles: UserRole) -> Callable:
    """
    Return a FastAPI dependency that enforces role-based access control.

    Usage::

        @router.delete("/{id}", dependencies=[Depends(require_roles(UserRole.TENANT_ADMIN))])
    """
    async def _check_roles(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if current_user.role not in roles:
            raise ForbiddenError(
                f"This action requires one of the following roles: "
                f"{', '.join(r.value for r in roles)}."
            )
        return current_user

    return _check_roles
