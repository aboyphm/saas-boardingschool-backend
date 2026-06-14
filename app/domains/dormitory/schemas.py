from __future__ import annotations

import uuid
from datetime import date, datetime

from app.shared.base_schema import BaseSchema
from app.shared.enums import DormitoryRoomStatus, DormitoryRoomType, Gender


class DormitoryBuildingCreate(BaseSchema):
    tenant_id: uuid.UUID
    name: str
    gender_type: Gender
    capacity: int
    location_notes: str | None = None


class DormitoryBuildingUpdate(BaseSchema):
    name: str | None = None
    capacity: int | None = None
    location_notes: str | None = None


class DormitoryBuildingResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    gender_type: Gender
    capacity: int
    location_notes: str | None
    created_at: datetime


class DormitoryRoomCreate(BaseSchema):
    tenant_id: uuid.UUID
    building_id: uuid.UUID
    room_number: str
    floor: int | None = None
    capacity: int
    room_type: DormitoryRoomType = DormitoryRoomType.STANDARD
    facilities: list[str] = []


class DormitoryRoomUpdate(BaseSchema):
    room_number: str | None = None
    floor: int | None = None
    capacity: int | None = None
    status: DormitoryRoomStatus | None = None
    room_type: DormitoryRoomType | None = None
    facilities: list[str] | None = None


class DormitoryRoomResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    building_id: uuid.UUID
    room_number: str
    floor: int | None
    capacity: int
    current_occupancy: int
    status: DormitoryRoomStatus
    room_type: DormitoryRoomType
    facilities: list
    created_at: datetime


class DormitoryAssignmentCreate(BaseSchema):
    tenant_id: uuid.UUID
    student_id: uuid.UUID
    room_id: uuid.UUID
    bed_number: str | None = None
    assigned_date: date


class DormitoryAssignmentResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    student_id: uuid.UUID
    room_id: uuid.UUID
    bed_number: str | None
    assigned_date: date
    vacated_date: date | None
    is_active: bool
    created_at: datetime


# ── Supervisor ─────────────────────────────────────────────────────────────
class DormitorySupervisorCreate(BaseSchema):
    teacher_id: uuid.UUID
    building_id: uuid.UUID
    assigned_date: date


class DormitorySupervisorResponse(BaseSchema):
    id: uuid.UUID
    teacher_id: uuid.UUID
    building_id: uuid.UUID
    assigned_date: date
    created_at: datetime


# ── Assignment enriched ────────────────────────────────────────────────────
class DormitoryAssignmentWithStudentResponse(BaseSchema):
    id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    room_id: uuid.UUID
    bed_number: str | None
    assigned_date: date
    is_active: bool


# ── Room enriched ──────────────────────────────────────────────────────────
class DormitoryRoomWithOccupantsResponse(BaseSchema):
    id: uuid.UUID
    room_number: str
    floor: int | None
    capacity: int
    current_occupancy: int
    status: str
    room_type: str
    facilities: list[str]
    assignments: list[DormitoryAssignmentWithStudentResponse]


# ── Building summary (for overview page) ──────────────────────────────────
class DormitoryBuildingSummaryResponse(BaseSchema):
    id: uuid.UUID
    name: str
    gender_type: str
    capacity: int
    current_occupancy: int
    available_beds: int
    room_count: int
    location_notes: str | None
    created_at: datetime
