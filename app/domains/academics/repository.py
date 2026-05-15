from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academics.models import AcademicYear, ClassRoom, Grade, Subject
from app.domains.academics.schemas import (
    AcademicYearCreate,
    AcademicYearUpdate,
    ClassRoomCreate,
    ClassRoomUpdate,
    GradeCreate,
    SubjectCreate,
    SubjectUpdate,
)
from app.shared.base_repository import BaseRepository


class AcademicYearRepository(BaseRepository[AcademicYear, AcademicYearCreate, AcademicYearUpdate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AcademicYear, session)

    async def get_active(self, tenant_id: uuid.UUID) -> AcademicYear | None:
        stmt = (
            select(AcademicYear)
            .where(AcademicYear.tenant_id == tenant_id, AcademicYear.is_active.is_(True))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class ClassRoomRepository(BaseRepository[ClassRoom, ClassRoomCreate, ClassRoomUpdate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ClassRoom, session)

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        academic_year_id: uuid.UUID | None = None,
    ) -> list[ClassRoom]:
        stmt = select(ClassRoom).where(ClassRoom.tenant_id == tenant_id)
        if academic_year_id is not None:
            stmt = stmt.where(ClassRoom.academic_year_id == academic_year_id)
        stmt = stmt.order_by(ClassRoom.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class SubjectRepository(BaseRepository[Subject, SubjectCreate, SubjectUpdate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Subject, session)

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[Subject]:
        stmt = (
            select(Subject)
            .where(Subject.tenant_id == tenant_id)
            .order_by(Subject.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class GradeRepository(BaseRepository[Grade, GradeCreate, GradeCreate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Grade, session)

    async def list_by_student(
        self,
        student_id: uuid.UUID,
        tenant_id: uuid.UUID,
        academic_year_id: uuid.UUID | None = None,
    ) -> list[Grade]:
        stmt = (
            select(Grade)
            .where(Grade.student_id == student_id, Grade.tenant_id == tenant_id)
        )
        if academic_year_id is not None:
            stmt = stmt.where(Grade.academic_year_id == academic_year_id)
        stmt = stmt.order_by(Grade.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
