from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.users.models import User, UserSession
from app.domains.users.schemas import UserCreate, UserUpdate
from app.shared.base_repository import BaseRepository
from app.shared.enums import UserRole


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_phone(self, phone: str, tenant_id: uuid.UUID | None = None) -> User | None:
        stmt = select(User).where(User.phone == phone, User.is_deleted.is_(False))
        if tenant_id is not None:
            stmt = stmt.where(User.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str, tenant_id: uuid.UUID | None = None) -> User | None:
        stmt = (
            select(User)
            .where(User.email == email, User.is_deleted.is_(False))
        )
        if tenant_id is not None:
            stmt = stmt.where(User.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_role_in_tenant(
        self, role: UserRole, tenant_id: uuid.UUID
    ) -> list[User]:
        stmt = (
            select(User)
            .where(
                User.role == role,
                User.tenant_id == tenant_id,
                User.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_session_by_token_hash(self, token_hash: str) -> UserSession | None:
        stmt = select(UserSession).where(
            UserSession.refresh_token_hash == token_hash,
            UserSession.is_revoked.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_session(self, session_data: dict) -> UserSession:
        user_session = UserSession(**session_data)
        self.session.add(user_session)
        await self.session.flush()
        await self.session.refresh(user_session)
        return user_session

    async def revoke_session(self, session_id: uuid.UUID) -> bool:
        stmt = select(UserSession).where(UserSession.id == session_id)
        result = await self.session.execute(stmt)
        user_session = result.scalar_one_or_none()
        if user_session is None:
            return False
        user_session.is_revoked = True
        self.session.add(user_session)
        await self.session.flush()
        return True

    async def save(self, user: User) -> User:
        """Persist a pre-constructed User model instance and return the refreshed object."""
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def list_with_search(
        self,
        tenant_id: uuid.UUID | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[User]:
        stmt = select(User).where(User.is_deleted.is_(False)).order_by(User.created_at.desc())
        if tenant_id is not None:
            stmt = stmt.where(User.tenant_id == tenant_id)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(or_(
                User.full_name.ilike(like),
                User.email.ilike(like),
                User.phone.ilike(like),
            ))
        result = await self.session.execute(stmt.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def count_with_search(
        self,
        tenant_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(User).where(User.is_deleted.is_(False))
        if tenant_id is not None:
            stmt = stmt.where(User.tenant_id == tenant_id)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(or_(
                User.full_name.ilike(like),
                User.email.ilike(like),
                User.phone.ilike(like),
            ))
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def revoke_all_sessions(self, user_id: uuid.UUID) -> None:
        stmt = (
            select(UserSession)
            .where(UserSession.user_id == user_id, UserSession.is_revoked.is_(False))
        )
        result = await self.session.execute(stmt)
        sessions = result.scalars().all()
        for s in sessions:
            s.is_revoked = True
            self.session.add(s)
        await self.session.flush()
