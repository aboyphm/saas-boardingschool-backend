from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academics.models import (
    AcademicYear,
    ClassEnrollment,
    ClassRoom,
    Grade,
    ScheduleSlot,
    SchoolEvent,
    Subject,
    SubjectGradeCurriculum,
)
from app.domains.academics.schemas import (
    AcademicYearCreate,
    AcademicYearUpdate,
    ClassEnrollmentResponse,
    ClassRoomCreate,
    ClassRoomUpdate,
    GradeCurriculumUpsert,
    GradeCreate,
    ScheduleSlotCreate,
    ScheduleSlotUpdate,
    SchoolEventCreate,
    SchoolEventUpdate,
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

    async def list_by_class(
        self,
        class_room_id: uuid.UUID,
        academic_year_id: uuid.UUID,
        semester: int,
        tenant_id: uuid.UUID,
    ) -> list[Grade]:
        stmt = (
            select(Grade)
            .join(
                ClassEnrollment,
                (ClassEnrollment.student_id == Grade.student_id)
                & (ClassEnrollment.academic_year_id == Grade.academic_year_id)
                & (ClassEnrollment.class_room_id == class_room_id)
                & ClassEnrollment.is_active.is_(True),
            )
            .where(
                Grade.academic_year_id == academic_year_id,
                Grade.semester == semester,
                Grade.tenant_id == tenant_id,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ClassEnrollmentRepository(BaseRepository[ClassEnrollment, ClassEnrollmentResponse, ClassEnrollmentResponse]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ClassEnrollment, session)

    async def list_by_class(
        self, class_room_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> list[ClassEnrollment]:
        stmt = (
            select(ClassEnrollment)
            .where(
                ClassEnrollment.class_room_id == class_room_id,
                ClassEnrollment.tenant_id == tenant_id,
                ClassEnrollment.is_active.is_(True),
            )
            .order_by(ClassEnrollment.enrolled_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_by_student_year(
        self,
        student_id: uuid.UUID,
        academic_year_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> ClassEnrollment | None:
        stmt = select(ClassEnrollment).where(
            ClassEnrollment.student_id == student_id,
            ClassEnrollment.academic_year_id == academic_year_id,
            ClassEnrollment.tenant_id == tenant_id,
            ClassEnrollment.is_active.is_(True),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_active_by_class(
        self, class_room_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> int:
        stmt = select(func.count()).where(
            ClassEnrollment.class_room_id == class_room_id,
            ClassEnrollment.tenant_id == tenant_id,
            ClassEnrollment.is_active.is_(True),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()


class SchoolEventRepository(BaseRepository[SchoolEvent, SchoolEventCreate, SchoolEventUpdate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(SchoolEvent, session)

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        academic_year_id: uuid.UUID | None = None,
    ) -> list[SchoolEvent]:
        stmt = select(SchoolEvent).where(SchoolEvent.tenant_id == tenant_id)
        if academic_year_id is not None:
            year = await self.session.get(AcademicYear, academic_year_id)
            if year:
                stmt = stmt.where(
                    SchoolEvent.date_from >= year.start_date,
                    SchoolEvent.date_to <= year.end_date,
                )
        stmt = stmt.order_by(SchoolEvent.date_from)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ScheduleSlotRepository(BaseRepository[ScheduleSlot, ScheduleSlotCreate, ScheduleSlotUpdate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ScheduleSlot, session)

    async def list_by_class_year(
        self,
        class_room_id: uuid.UUID,
        academic_year_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[ScheduleSlot]:
        stmt = (
            select(ScheduleSlot)
            .where(
                ScheduleSlot.class_room_id == class_room_id,
                ScheduleSlot.academic_year_id == academic_year_id,
                ScheduleSlot.tenant_id == tenant_id,
            )
            .order_by(ScheduleSlot.day_of_week, ScheduleSlot.time_start)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def check_overlap(
        self,
        class_room_id: uuid.UUID,
        academic_year_id: uuid.UUID,
        day_of_week: str,
        time_start: str,
        tenant_id: uuid.UUID,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        stmt = select(ScheduleSlot).where(
            ScheduleSlot.class_room_id == class_room_id,
            ScheduleSlot.academic_year_id == academic_year_id,
            ScheduleSlot.day_of_week == day_of_week,
            ScheduleSlot.time_start == time_start,
            ScheduleSlot.tenant_id == tenant_id,
        )
        if exclude_id:
            stmt = stmt.where(ScheduleSlot.id != exclude_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None


class GradeCurriculumRepository(
    BaseRepository[SubjectGradeCurriculum, GradeCurriculumUpsert, GradeCurriculumUpsert]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(SubjectGradeCurriculum, session)

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[SubjectGradeCurriculum]:
        stmt = (
            select(SubjectGradeCurriculum)
            .where(SubjectGradeCurriculum.tenant_id == tenant_id)
            .order_by(SubjectGradeCurriculum.grade_level, SubjectGradeCurriculum.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_subject_grade(
        self, subject_id: uuid.UUID, grade_level: str, tenant_id: uuid.UUID
    ) -> SubjectGradeCurriculum | None:
        stmt = select(SubjectGradeCurriculum).where(
            SubjectGradeCurriculum.subject_id == subject_id,
            SubjectGradeCurriculum.grade_level == grade_level,
            SubjectGradeCurriculum.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_entry(
        self, subject_id: uuid.UUID, grade_level: str, tenant_id: uuid.UUID
    ) -> bool:
        entry = await self.get_by_subject_grade(subject_id, grade_level, tenant_id)
        if entry is None:
            return False
        await self.session.delete(entry)
        await self.session.flush()
        return True
