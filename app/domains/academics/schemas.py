from __future__ import annotations

import uuid
from datetime import date, datetime

from app.shared.base_schema import BaseSchema
from app.shared.enums import DayOfWeek, SchoolEventType, SubjectType


class AcademicYearCreate(BaseSchema):
    tenant_id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    is_active: bool = False
    semester_1_start: date | None = None
    semester_1_end: date | None = None
    semester_2_start: date | None = None
    semester_2_end: date | None = None


class AcademicYearUpdate(BaseSchema):
    name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool | None = None
    semester_1_start: date | None = None
    semester_1_end: date | None = None
    semester_2_start: date | None = None
    semester_2_end: date | None = None


class AcademicYearResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    is_active: bool
    created_at: datetime
    semester_1_start: date | None = None
    semester_1_end: date | None = None
    semester_2_start: date | None = None
    semester_2_end: date | None = None


class ClassRoomCreate(BaseSchema):
    tenant_id: uuid.UUID
    academic_year_id: uuid.UUID
    name: str
    grade_level: str
    homeroom_teacher_id: uuid.UUID | None = None
    capacity: int = 30


class ClassRoomUpdate(BaseSchema):
    name: str | None = None
    grade_level: str | None = None
    homeroom_teacher_id: uuid.UUID | None = None
    capacity: int | None = None
    current_count: int | None = None


class ClassRoomResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    academic_year_id: uuid.UUID
    name: str
    grade_level: str
    homeroom_teacher_id: uuid.UUID | None
    capacity: int
    current_count: int
    created_at: datetime


class SubjectCreate(BaseSchema):
    tenant_id: uuid.UUID
    code: str
    name: str
    description: str | None = None
    credit_hours: int = 2
    subject_type: SubjectType = SubjectType.GENERAL


class SubjectUpdate(BaseSchema):
    name: str | None = None
    description: str | None = None
    credit_hours: int | None = None
    subject_type: SubjectType | None = None


class SubjectResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    name: str
    description: str | None
    credit_hours: int
    subject_type: SubjectType
    created_at: datetime


class GradeCreate(BaseSchema):
    tenant_id: uuid.UUID
    student_id: uuid.UUID
    subject_id: uuid.UUID
    academic_year_id: uuid.UUID
    semester: int
    score: float
    grade_letter: str | None = None
    notes: str | None = None


class GradeResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    student_id: uuid.UUID
    subject_id: uuid.UUID
    academic_year_id: uuid.UUID
    semester: int
    score: float
    grade_letter: str | None
    notes: str | None
    created_at: datetime


# ── ClassEnrollment ────────────────────────────────────────────────────────
class EnrollStudentRequest(BaseSchema):
    student_id: uuid.UUID
    academic_year_id: uuid.UUID
    enrolled_at: date


class ClassEnrollmentResponse(BaseSchema):
    id: uuid.UUID
    student_id: uuid.UUID
    class_room_id: uuid.UUID
    academic_year_id: uuid.UUID
    enrolled_at: date
    is_active: bool


# ── SchoolEvent ────────────────────────────────────────────────────────────
class SchoolEventCreate(BaseSchema):
    title: str
    date_from: date
    date_to: date
    event_type: SchoolEventType
    description: str | None = None


class SchoolEventUpdate(BaseSchema):
    title: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    event_type: SchoolEventType | None = None
    description: str | None = None


class SchoolEventResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    date_from: date
    date_to: date
    event_type: SchoolEventType
    description: str | None = None
    created_at: datetime


# ── ScheduleSlot ───────────────────────────────────────────────────────────
class ScheduleSlotCreate(BaseSchema):
    class_room_id: uuid.UUID
    academic_year_id: uuid.UUID
    subject_id: uuid.UUID
    teacher_id: uuid.UUID | None = None
    day_of_week: DayOfWeek
    time_start: str
    time_end: str


class ScheduleSlotUpdate(BaseSchema):
    subject_id: uuid.UUID | None = None
    teacher_id: uuid.UUID | None = None
    time_start: str | None = None
    time_end: str | None = None


class ScheduleSlotResponse(BaseSchema):
    id: uuid.UUID
    class_room_id: uuid.UUID
    academic_year_id: uuid.UUID
    subject_id: uuid.UUID
    teacher_id: uuid.UUID | None = None
    day_of_week: DayOfWeek
    time_start: str
    time_end: str


# ── Grades batch ───────────────────────────────────────────────────────────
class GradeBatchItem(BaseSchema):
    student_id: uuid.UUID
    subject_id: uuid.UUID
    score: float
    semester: int
    academic_year_id: uuid.UUID


class GradeBatchRequest(BaseSchema):
    grades: list[GradeBatchItem]


class StudentGradeMatrixRow(BaseSchema):
    student_id: uuid.UUID
    student_name: str
    grades: dict[str, float | None]


class ClassGradeMatrixResponse(BaseSchema):
    rows: list[StudentGradeMatrixRow]
    subject_ids: list[str]


# ── Grade Curriculum ───────────────────────────────────────────────────────
class GradeCurriculumUpsert(BaseSchema):
    subject_id: uuid.UUID
    grade_level: str
    is_lead: bool = False


class GradeCurriculumResponse(BaseSchema):
    id: uuid.UUID
    subject_id: uuid.UUID
    grade_level: str
    is_lead: bool


class GradeCurriculumRow(BaseSchema):
    """One subject row in the curriculum matrix, with grade assignments."""
    subject_id: uuid.UUID
    subject_code: str
    subject_name: str
    subject_type: str
    grades: dict[str, bool]  # grade_level -> is_lead (key absent = not in curriculum)
