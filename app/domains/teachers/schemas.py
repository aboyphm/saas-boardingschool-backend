from __future__ import annotations

import uuid
from datetime import date, datetime

from app.shared.base_schema import BaseSchema
from app.shared.enums import EmploymentType, Gender


class TeacherCreate(BaseSchema):
    tenant_id: uuid.UUID
    nip: str
    full_name: str
    gender: Gender
    phone: str | None = None
    dial_code: str = "62"
    birth_date: date | None = None
    specialization: str | None = None
    qualification: str | None = None
    subjects: list[str] = []
    grade_levels: list[str] = []
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    join_date: date | None = None
    user_id: uuid.UUID | None = None


class TeacherUpdate(BaseSchema):
    full_name: str | None = None
    gender: Gender | None = None
    phone: str | None = None
    dial_code: str = "62"
    birth_date: date | None = None
    specialization: str | None = None
    qualification: str | None = None
    subjects: list[str] | None = None
    grade_levels: list[str] | None = None
    employment_type: EmploymentType | None = None
    is_homeroom_teacher: bool | None = None
    homeroom_class_id: uuid.UUID | None = None


class TeacherResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    nip: str
    full_name: str
    gender: Gender
    phone: str | None
    birth_date: date | None
    specialization: str | None
    qualification: str | None
    subjects: list
    grade_levels: list
    is_homeroom_teacher: bool
    homeroom_class_id: uuid.UUID | None
    employment_type: EmploymentType
    join_date: date | None
    created_at: datetime
