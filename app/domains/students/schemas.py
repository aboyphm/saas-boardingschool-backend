from __future__ import annotations

import uuid
from datetime import date, datetime

from app.shared.base_schema import BaseSchema
from app.shared.enums import Gender, ParentRelationship, StudentStatus


class StudentCreate(BaseSchema):
    tenant_id: uuid.UUID
    full_name: str
    nis: str
    gender: Gender
    birth_date: date | None = None
    birth_place: str | None = None
    religion: str = "Islam"
    nationality: str = "Indonesian"
    address: str | None = None
    city: str | None = None
    phone: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    blood_type: str | None = None
    health_notes: str | None = None
    status: StudentStatus = StudentStatus.ACTIVE
    enrollment_date: date | None = None
    academic_year: str | None = None
    class_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None


class StudentUpdate(BaseSchema):
    full_name: str | None = None
    gender: Gender | None = None
    birth_date: date | None = None
    birth_place: str | None = None
    address: str | None = None
    city: str | None = None
    phone: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    blood_type: str | None = None
    health_notes: str | None = None
    status: StudentStatus | None = None
    class_id: uuid.UUID | None = None
    dormitory_room_id: uuid.UUID | None = None
    photo_url: str | None = None
    academic_year: str | None = None


class StudentResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    nis: str
    full_name: str
    gender: Gender
    birth_date: date | None
    birth_place: str | None
    religion: str
    phone: str | None
    photo_url: str | None
    blood_type: str | None
    status: StudentStatus
    enrollment_date: date | None
    academic_year: str | None
    class_id: uuid.UUID | None
    dormitory_room_id: uuid.UUID | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    created_at: datetime
    updated_at: datetime


class StudentParentCreate(BaseSchema):
    student_id: uuid.UUID
    parent_user_id: uuid.UUID
    relationship_type: ParentRelationship
    is_primary: bool = False
