from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.teachers.models import Teacher
from app.domains.teachers.schemas import TeacherCreate, TeacherUpdate
from app.shared.base_repository import BaseRepository


class TeacherRepository(BaseRepository[Teacher, TeacherCreate, TeacherUpdate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Teacher, session)

    async def search(
        self,
        tenant_id: uuid.UUID,
        query: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Teacher]:
        stmt = self._base_query().where(Teacher.tenant_id == tenant_id)
        if query:
            term = f"%{query}%"
            stmt = stmt.where(
                or_(
                    Teacher.full_name.ilike(term),
                    Teacher.nip.ilike(term),
                )
            )
        stmt = stmt.order_by(Teacher.full_name).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_nip(self, nip: str, tenant_id: uuid.UUID) -> Teacher | None:
        stmt = (
            self._base_query()
            .where(Teacher.nip == nip, Teacher.tenant_id == tenant_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
