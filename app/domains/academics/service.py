from __future__ import annotations

import uuid

from app.core.exceptions import ConflictError, NotFoundError
from app.domains.academics.models import AcademicYear, ClassRoom, Grade, Subject
from app.domains.academics.repository import (
    AcademicYearRepository,
    ClassRoomRepository,
    GradeRepository,
    SubjectRepository,
)
from app.domains.academics.schemas import (
    AcademicYearCreate,
    AcademicYearUpdate,
    ClassRoomCreate,
    ClassRoomUpdate,
    GradeCreate,
    SubjectCreate,
    SubjectUpdate,
)


class AcademicsService:
    def __init__(
        self,
        year_repo: AcademicYearRepository,
        class_repo: ClassRoomRepository,
        subject_repo: SubjectRepository,
        grade_repo: GradeRepository,
    ) -> None:
        self.year_repo = year_repo
        self.class_repo = class_repo
        self.subject_repo = subject_repo
        self.grade_repo = grade_repo

    # ─── Academic years ───────────────────────────────────────────────────────
    async def create_year(self, data: AcademicYearCreate) -> AcademicYear:
        if await self.year_repo.exists({"tenant_id": data.tenant_id, "name": data.name}):
            raise ConflictError(f"Academic year '{data.name}' already exists.")
        year = AcademicYear(**data.model_dump())
        self.year_repo.session.add(year)
        await self.year_repo.session.flush()
        await self.year_repo.session.refresh(year)
        return year

    async def list_years(self, tenant_id: uuid.UUID) -> list[AcademicYear]:
        return await self.year_repo.list(filters={"tenant_id": tenant_id})

    # ─── Classes ──────────────────────────────────────────────────────────────
    async def create_class(self, data: ClassRoomCreate) -> ClassRoom:
        classroom = ClassRoom(**data.model_dump())
        self.class_repo.session.add(classroom)
        await self.class_repo.session.flush()
        await self.class_repo.session.refresh(classroom)
        return classroom

    async def list_classes(
        self,
        tenant_id: uuid.UUID,
        academic_year_id: uuid.UUID | None = None,
    ) -> list[ClassRoom]:
        return await self.class_repo.list_by_tenant(tenant_id, academic_year_id)

    async def get_class_or_404(
        self, class_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> ClassRoom:
        classroom = await self.class_repo.get_by_tenant(class_id, tenant_id)
        if classroom is None:
            raise NotFoundError("Class not found.")
        return classroom

    # ─── Subjects ─────────────────────────────────────────────────────────────
    async def create_subject(self, data: SubjectCreate) -> Subject:
        if await self.subject_repo.exists({"tenant_id": data.tenant_id, "code": data.code}):
            raise ConflictError(f"Subject code '{data.code}' already exists.")
        subject = Subject(**data.model_dump())
        self.subject_repo.session.add(subject)
        await self.subject_repo.session.flush()
        await self.subject_repo.session.refresh(subject)
        return subject

    async def list_subjects(self, tenant_id: uuid.UUID) -> list[Subject]:
        return await self.subject_repo.list_by_tenant(tenant_id)

    # ─── Grades ───────────────────────────────────────────────────────────────
    async def record_grade(self, data: GradeCreate) -> Grade:
        grade = Grade(**data.model_dump())
        self.grade_repo.session.add(grade)
        await self.grade_repo.session.flush()
        await self.grade_repo.session.refresh(grade)
        return grade

    async def get_student_grades(
        self,
        student_id: uuid.UUID,
        tenant_id: uuid.UUID,
        academic_year_id: uuid.UUID | None = None,
    ) -> list[Grade]:
        return await self.grade_repo.list_by_student(
            student_id=student_id,
            tenant_id=tenant_id,
            academic_year_id=academic_year_id,
        )
