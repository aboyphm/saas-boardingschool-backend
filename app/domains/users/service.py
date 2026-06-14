from __future__ import annotations

import uuid

from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.core.security import get_password_hash, verify_password
from app.domains.users.models import User
from app.domains.users.repository import UserRepository
from app.domains.users.schemas import ChangePasswordRequest, UserCreate, UserUpdate
from app.shared.pagination import PaginationParams


def _normalize_phone(phone: str, dial_code: str = "62") -> str:
    digits = "".join(c for c in phone if c.isdigit())
    if digits.startswith("0"):
        digits = dial_code + digits[1:]
    return digits


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def list_users(
        self,
        pagination: PaginationParams,
        tenant_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> tuple[list[User], int]:
        items = await self.repository.list_with_search(
            tenant_id=tenant_id,
            search=search,
            skip=pagination.offset,
            limit=pagination.size,
        )
        total = await self.repository.count_with_search(
            tenant_id=tenant_id,
            search=search,
        )
        return items, total

    async def create_user(self, data: UserCreate) -> User:
        """Create a new user — account starts inactive until phone is verified via OTP."""
        existing = await self.repository.get_by_email(data.email, data.tenant_id)
        if existing is not None:
            raise ConflictError(f"A user with email '{data.email}' already exists.")

        if data.phone:
            data.phone = _normalize_phone(data.phone, data.dial_code)
            phone_existing = await self.repository.get_by_phone(data.phone, data.tenant_id)
            if phone_existing is not None:
                raise ConflictError(f"A user with phone '{data.phone}' already exists.")
            # Warn if phone exists in another tenant — cross-tenant collision causes OTP login ambiguity
            global_existing = await self.repository.get_by_phone(data.phone)
            if global_existing and global_existing.tenant_id != data.tenant_id:
                import logging as _logging
                _logging.getLogger(__name__).warning(
                    "Phone %s already exists in tenant %s — cross-tenant collision will cause OTP ambiguity",
                    data.phone, global_existing.tenant_id,
                )

        hashed = get_password_hash(data.password)
        user_data = data.model_dump(exclude={"password"})
        user_data["password_hash"] = hashed
        user_data["is_active"] = False
        user_data["is_verified"] = False

        user = User(**user_data)
        self.repository.session.add(user)
        await self.repository.session.flush()
        await self.repository.session.refresh(user)
        return user

    async def get_or_404(self, user_id: uuid.UUID) -> User:
        user = await self.repository.get(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        return user

    async def update_user(self, user_id: uuid.UUID, data: UserUpdate) -> User:
        updated = await self.repository.update(user_id, data)
        if updated is None:
            raise NotFoundError("User not found.")
        return updated

    async def change_password(
        self, user_id: uuid.UUID, data: ChangePasswordRequest
    ) -> User:
        user = await self.get_or_404(user_id)
        if not verify_password(data.current_password, user.password_hash):
            raise UnauthorizedError("Current password is incorrect.")
        user.password_hash = get_password_hash(data.new_password)
        self.repository.session.add(user)
        await self.repository.session.flush()
        await self.repository.session.refresh(user)
        return user

    async def deactivate(self, user_id: uuid.UUID) -> User:
        user = await self.get_or_404(user_id)
        user.is_active = False
        self.repository.session.add(user)
        await self.repository.session.flush()
        await self.repository.session.refresh(user)
        return user
