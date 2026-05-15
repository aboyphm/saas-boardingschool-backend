from __future__ import annotations

import uuid
from datetime import date, datetime

from app.shared.base_schema import BaseSchema
from app.shared.enums import SubjectType


class AcademicYearCreate(BaseSchema):
    tenant_id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    is_active: bool = False


class AcademicYearUpdate(BaseSchema):
    name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool | None = None


class AcademicYearResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    is_active: bool
    created_at: datetime


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
