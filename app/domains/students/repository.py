from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.students.models import Student, StudentParent
from app.domains.students.schemas import StudentCreate, StudentUpdate
from app.shared.base_repository import BaseRepository
from app.shared.enums import StudentStatus


class StudentRepository(BaseRepository[Student, StudentCreate, StudentUpdate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Student, session)

    async def search(
        self,
        tenant_id: uuid.UUID,
        query: str | None = None,
        status: StudentStatus | None = None,
        class_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Student]:
        stmt = (
            self._base_query()
            .where(Student.tenant_id == tenant_id)
        )
        if status is not None:
            stmt = stmt.where(Student.status == status)
        if class_id is not None:
            stmt = stmt.where(Student.class_id == class_id)
        if query:
            search_term = f"%{query}%"
            stmt = stmt.where(
                or_(
                    Student.full_name.ilike(search_term),
                    Student.nis.ilike(search_term),
                )
            )
        stmt = stmt.order_by(Student.full_name).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_search(
        self,
        tenant_id: uuid.UUID,
        query: str | None = None,
        status: StudentStatus | None = None,
        class_id: uuid.UUID | None = None,
    ) -> int:
        from sqlalchemy import func
        stmt = (
            select(func.count())
            .select_from(Student)
            .where(Student.tenant_id == tenant_id, Student.is_deleted.is_(False))
        )
        if status is not None:
            stmt = stmt.where(Student.status == status)
        if class_id is not None:
            stmt = stmt.where(Student.class_id == class_id)
        if query:
            search_term = f"%{query}%"
            stmt = stmt.where(
                or_(Student.full_name.ilike(search_term), Student.nis.ilike(search_term))
            )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_by_nis(self, nis: str, tenant_id: uuid.UUID) -> Student | None:
        stmt = (
            self._base_query()
            .where(Student.nis == nis, Student.tenant_id == tenant_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
