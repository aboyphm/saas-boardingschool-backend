from __future__ import annotations

import uuid

from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.core.security import get_password_hash, verify_password
from app.domains.users.models import User
from app.domains.users.repository import UserRepository
from app.domains.users.schemas import ChangePasswordRequest, UserCreate, UserUpdate


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def create_user(self, data: UserCreate) -> User:
        """Create a new user, hashing the password before persistence."""
        existing = await self.repository.get_by_email(data.email, data.tenant_id)
        if existing is not None:
            raise ConflictError(f"A user with email '{data.email}' already exists.")

        hashed = get_password_hash(data.password)
        user_data = data.model_dump(exclude={"password"})
        user_data["password_hash"] = hashed

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
