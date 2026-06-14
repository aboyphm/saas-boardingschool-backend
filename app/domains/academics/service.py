from __future__ import annotations

import uuid

from sqlalchemy import select

from app.core.exceptions import ConflictError, NotFoundError
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
from app.domains.academics.repository import (
    AcademicYearRepository,
    ClassEnrollmentRepository,
    ClassRoomRepository,
    GradeCurriculumRepository,
    GradeRepository,
    ScheduleSlotRepository,
    SchoolEventRepository,
    SubjectRepository,
)
from app.domains.academics.schemas import (
    AcademicYearCreate,
    AcademicYearUpdate,
    ClassGradeMatrixResponse,
    ClassRoomCreate,
    ClassRoomUpdate,
    EnrollStudentRequest,
    GradeBatchItem,
    GradeCurriculumResponse,
    GradeCurriculumRow,
    GradeCurriculumUpsert,
    GradeCreate,
    ScheduleSlotCreate,
    ScheduleSlotUpdate,
    SchoolEventCreate,
    SchoolEventUpdate,
    StudentGradeMatrixRow,
    SubjectCreate,
    SubjectUpdate,
)
from app.domains.students.models import Student


class AcademicsService:
    def __init__(
        self,
        year_repo: AcademicYearRepository,
        class_repo: ClassRoomRepository,
        subject_repo: SubjectRepository,
        grade_repo: GradeRepository,
        enrollment_repo: ClassEnrollmentRepository,
        event_repo: SchoolEventRepository,
        slot_repo: ScheduleSlotRepository,
        curriculum_repo: GradeCurriculumRepository,
    ) -> None:
        self.year_repo = year_repo
        self.class_repo = class_repo
        self.subject_repo = subject_repo
        self.grade_repo = grade_repo
        self.enrollment_repo = enrollment_repo
        self.event_repo = event_repo
        self.slot_repo = slot_repo
        self.curriculum_repo = curriculum_repo

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

    # ─── Academic years: complete CRUD ────────────────────────────────────────
    async def get_year_or_404(self, year_id: uuid.UUID, tenant_id: uuid.UUID) -> AcademicYear:
        year = await self.year_repo.get_by_tenant(year_id, tenant_id)
        if year is None:
            raise NotFoundError("Academic year not found.")
        return year

    async def update_year(
        self, year_id: uuid.UUID, data: AcademicYearUpdate, tenant_id: uuid.UUID
    ) -> AcademicYear:
        year = await self.get_year_or_404(year_id, tenant_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(year, field, value)
        await self.year_repo.session.flush()
        await self.year_repo.session.refresh(year)
        return year

    async def delete_year(self, year_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        year = await self.get_year_or_404(year_id, tenant_id)
        classes = await self.class_repo.list_by_tenant(tenant_id, year_id)
        if classes:
            raise ConflictError("Hapus kelas terlebih dahulu sebelum menghapus tahun ajaran.")
        await self.year_repo.session.delete(year)
        await self.year_repo.session.flush()

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

    # ─── Classes: complete CRUD ────────────────────────────────────────────────
    async def update_class(
        self, class_id: uuid.UUID, data: ClassRoomUpdate, tenant_id: uuid.UUID
    ) -> ClassRoom:
        classroom = await self.get_class_or_404(class_id, tenant_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(classroom, field, value)
        await self.class_repo.session.flush()
        await self.class_repo.session.refresh(classroom)
        return classroom

    async def delete_class(self, class_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        classroom = await self.get_class_or_404(class_id, tenant_id)
        await self.class_repo.session.delete(classroom)
        await self.class_repo.session.flush()

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

    # ─── Subjects: complete CRUD ───────────────────────────────────────────────
    async def get_subject_or_404(self, subject_id: uuid.UUID, tenant_id: uuid.UUID) -> Subject:
        subject = await self.subject_repo.get_by_tenant(subject_id, tenant_id)
        if subject is None:
            raise NotFoundError("Subject not found.")
        return subject

    async def update_subject(
        self, subject_id: uuid.UUID, data: SubjectUpdate, tenant_id: uuid.UUID
    ) -> Subject:
        subject = await self.get_subject_or_404(subject_id, tenant_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(subject, field, value)
        await self.subject_repo.session.flush()
        await self.subject_repo.session.refresh(subject)
        return subject

    async def delete_subject(self, subject_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        subject = await self.get_subject_or_404(subject_id, tenant_id)
        await self.subject_repo.session.delete(subject)
        await self.subject_repo.session.flush()

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

    # ─── Enrollment ────────────────────────────────────────────────────────────
    async def enroll_student(
        self,
        class_id: uuid.UUID,
        data: EnrollStudentRequest,
        tenant_id: uuid.UUID,
    ) -> ClassEnrollment:
        classroom = await self.get_class_or_404(class_id, tenant_id)
        existing = await self.enrollment_repo.get_active_by_student_year(
            data.student_id, data.academic_year_id, tenant_id
        )
        if existing:
            raise ConflictError("Siswa sudah terdaftar di kelas ini atau kelas lain pada tahun ajaran yang sama.")
        enrolled_count = await self.enrollment_repo.count_active_by_class(class_id, tenant_id)
        if enrolled_count >= classroom.capacity:
            raise ConflictError("Kelas sudah penuh.")
        enrollment = ClassEnrollment(
            tenant_id=tenant_id,
            student_id=data.student_id,
            class_room_id=class_id,
            academic_year_id=data.academic_year_id,
            enrolled_at=data.enrolled_at,
        )
        self.enrollment_repo.session.add(enrollment)
        classroom.current_count = enrolled_count + 1
        await self.enrollment_repo.session.flush()
        await self.enrollment_repo.session.refresh(enrollment)
        return enrollment

    async def remove_enrollment(
        self, class_id: uuid.UUID, student_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        classroom = await self.get_class_or_404(class_id, tenant_id)
        stmt = select(ClassEnrollment).where(
            ClassEnrollment.class_room_id == class_id,
            ClassEnrollment.student_id == student_id,
            ClassEnrollment.tenant_id == tenant_id,
            ClassEnrollment.is_active.is_(True),
        )
        result = await self.enrollment_repo.session.execute(stmt)
        enrollment = result.scalar_one_or_none()
        if enrollment is None:
            raise NotFoundError("Enrollment not found.")
        enrollment.is_active = False
        classroom.current_count = max(0, classroom.current_count - 1)
        await self.enrollment_repo.session.flush()

    async def list_class_enrollments(
        self, class_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> list[ClassEnrollment]:
        return await self.enrollment_repo.list_by_class(class_id, tenant_id)

    # ─── Grade matrix ──────────────────────────────────────────────────────────
    async def list_class_grades(
        self,
        class_id: uuid.UUID,
        academic_year_id: uuid.UUID,
        semester: int,
        tenant_id: uuid.UUID,
    ) -> ClassGradeMatrixResponse:
        enrollments = await self.enrollment_repo.list_by_class(class_id, tenant_id)
        grades = await self.grade_repo.list_by_class(
            class_id, academic_year_id, semester, tenant_id
        )
        subjects = await self.subject_repo.list_by_tenant(tenant_id)
        subject_ids = [str(s.id) for s in subjects]

        grade_map: dict[str, dict[str, float]] = {}
        for g in grades:
            sid = str(g.student_id)
            if sid not in grade_map:
                grade_map[sid] = {}
            grade_map[sid][str(g.subject_id)] = g.score

        rows = []
        for e in enrollments:
            student = await self.enrollment_repo.session.get(Student, e.student_id)
            rows.append(StudentGradeMatrixRow(
                student_id=e.student_id,
                student_name=student.full_name if student else str(e.student_id),
                grades={sid: grade_map.get(str(e.student_id), {}).get(sid) for sid in subject_ids},
            ))

        return ClassGradeMatrixResponse(rows=rows, subject_ids=subject_ids)

    async def batch_upsert_grades(
        self, items: list[GradeBatchItem], tenant_id: uuid.UUID
    ) -> int:
        def score_to_letter(score: float) -> str:
            if score >= 90:
                return "A"
            if score >= 80:
                return "B+"
            if score >= 70:
                return "B"
            if score >= 60:
                return "C+"
            if score >= 50:
                return "C"
            return "D"

        count = 0
        for item in items:
            stmt = select(Grade).where(
                Grade.student_id == item.student_id,
                Grade.subject_id == item.subject_id,
                Grade.academic_year_id == item.academic_year_id,
                Grade.semester == item.semester,
                Grade.tenant_id == tenant_id,
            )
            result = await self.grade_repo.session.execute(stmt)
            grade = result.scalar_one_or_none()
            if grade:
                grade.score = item.score
                grade.grade_letter = score_to_letter(item.score)
            else:
                grade = Grade(
                    tenant_id=tenant_id,
                    student_id=item.student_id,
                    subject_id=item.subject_id,
                    academic_year_id=item.academic_year_id,
                    semester=item.semester,
                    score=item.score,
                    grade_letter=score_to_letter(item.score),
                )
                self.grade_repo.session.add(grade)
            count += 1
        await self.grade_repo.session.flush()
        return count

    # ─── School events ─────────────────────────────────────────────────────────
    async def create_event(
        self, data: SchoolEventCreate, tenant_id: uuid.UUID
    ) -> SchoolEvent:
        event = SchoolEvent(
            tenant_id=tenant_id,
            title=data.title,
            date_from=data.date_from,
            date_to=data.date_to,
            event_type=data.event_type.value if hasattr(data.event_type, "value") else data.event_type,
            description=data.description,
        )
        self.event_repo.session.add(event)
        await self.event_repo.session.flush()
        await self.event_repo.session.refresh(event)
        return event

    async def list_events(
        self, tenant_id: uuid.UUID, academic_year_id: uuid.UUID | None = None
    ) -> list[SchoolEvent]:
        return await self.event_repo.list_by_tenant(tenant_id, academic_year_id)

    async def update_event(
        self, event_id: uuid.UUID, data: SchoolEventUpdate, tenant_id: uuid.UUID
    ) -> SchoolEvent:
        event = await self.event_repo.get_by_tenant(event_id, tenant_id)
        if event is None:
            raise NotFoundError("Event not found.")
        for field, value in data.model_dump(exclude_none=True).items():
            if field == "event_type" and hasattr(value, "value"):
                value = value.value
            setattr(event, field, value)
        await self.event_repo.session.flush()
        await self.event_repo.session.refresh(event)
        return event

    async def delete_event(self, event_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        event = await self.event_repo.get_by_tenant(event_id, tenant_id)
        if event is None:
            raise NotFoundError("Event not found.")
        await self.event_repo.session.delete(event)
        await self.event_repo.session.flush()

    # ─── Timetable ─────────────────────────────────────────────────────────────
    async def create_slot(
        self, data: ScheduleSlotCreate, tenant_id: uuid.UUID
    ) -> ScheduleSlot:
        overlap = await self.slot_repo.check_overlap(
            data.class_room_id,
            data.academic_year_id,
            data.day_of_week.value if hasattr(data.day_of_week, "value") else data.day_of_week,
            data.time_start,
            tenant_id,
        )
        if overlap:
            raise ConflictError("Slot waktu sudah digunakan untuk kelas ini.")
        slot = ScheduleSlot(
            tenant_id=tenant_id,
            class_room_id=data.class_room_id,
            academic_year_id=data.academic_year_id,
            subject_id=data.subject_id,
            teacher_id=data.teacher_id,
            day_of_week=data.day_of_week.value if hasattr(data.day_of_week, "value") else data.day_of_week,
            time_start=data.time_start,
            time_end=data.time_end,
        )
        self.slot_repo.session.add(slot)
        await self.slot_repo.session.flush()
        await self.slot_repo.session.refresh(slot)
        return slot

    async def list_timetable(
        self, class_id: uuid.UUID, academic_year_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> list[ScheduleSlot]:
        return await self.slot_repo.list_by_class_year(class_id, academic_year_id, tenant_id)

    async def update_slot(
        self, slot_id: uuid.UUID, data: ScheduleSlotUpdate, tenant_id: uuid.UUID
    ) -> ScheduleSlot:
        slot = await self.slot_repo.get_by_tenant(slot_id, tenant_id)
        if slot is None:
            raise NotFoundError("Schedule slot not found.")
        if data.time_start and data.time_start != slot.time_start:
            overlap = await self.slot_repo.check_overlap(
                slot.class_room_id,
                slot.academic_year_id,
                slot.day_of_week,
                data.time_start,
                tenant_id,
                exclude_id=slot_id,
            )
            if overlap:
                raise ConflictError("Slot waktu sudah digunakan.")
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(slot, field, value)
        await self.slot_repo.session.flush()
        await self.slot_repo.session.refresh(slot)
        return slot

    async def delete_slot(self, slot_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        slot = await self.slot_repo.get_by_tenant(slot_id, tenant_id)
        if slot is None:
            raise NotFoundError("Schedule slot not found.")
        await self.slot_repo.session.delete(slot)
        await self.slot_repo.session.flush()

    # ── Grade Curriculum ───────────────────────────────────────────────────────
    async def list_curriculum_matrix(
        self, tenant_id: uuid.UUID
    ) -> list[GradeCurriculumRow]:
        entries = await self.curriculum_repo.list_by_tenant(tenant_id)
        subjects = await self.subject_repo.list_by_tenant(tenant_id)

        assignment_map: dict[uuid.UUID, dict[str, bool]] = {}
        for entry in entries:
            if entry.subject_id not in assignment_map:
                assignment_map[entry.subject_id] = {}
            assignment_map[entry.subject_id][entry.grade_level] = entry.is_lead

        rows = []
        for subj in subjects:
            rows.append(GradeCurriculumRow(
                subject_id=subj.id,
                subject_code=subj.code,
                subject_name=subj.name,
                subject_type=str(subj.subject_type),
                grades=assignment_map.get(subj.id, {}),
            ))
        return rows

    async def upsert_curriculum(
        self, data: GradeCurriculumUpsert, tenant_id: uuid.UUID
    ) -> SubjectGradeCurriculum:
        existing = await self.curriculum_repo.get_by_subject_grade(
            data.subject_id, data.grade_level, tenant_id
        )
        if existing:
            existing.is_lead = data.is_lead
            await self.curriculum_repo.session.flush()
            await self.curriculum_repo.session.refresh(existing)
            return existing
        entry = SubjectGradeCurriculum(
            tenant_id=tenant_id,
            subject_id=data.subject_id,
            grade_level=data.grade_level,
            is_lead=data.is_lead,
        )
        self.curriculum_repo.session.add(entry)
        await self.curriculum_repo.session.flush()
        await self.curriculum_repo.session.refresh(entry)
        return entry

    async def remove_curriculum(
        self, subject_id: uuid.UUID, grade_level: str, tenant_id: uuid.UUID
    ) -> None:
        removed = await self.curriculum_repo.delete_entry(subject_id, grade_level, tenant_id)
        if not removed:
            raise NotFoundError("Curriculum entry not found.")
