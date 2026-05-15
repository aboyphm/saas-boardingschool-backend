from __future__ import annotations

import uuid
from datetime import date, datetime

from app.shared.base_schema import BaseSchema
from app.shared.enums import AttendanceInputMethod, AttendanceStatus, LeaveRequestStatus


class AttendanceCheckIn(BaseSchema):
    tenant_id: uuid.UUID
    student_id: uuid.UUID
    date: date
    status: AttendanceStatus = AttendanceStatus.PRESENT
    class_id: uuid.UUID | None = None
    input_method: AttendanceInputMethod = AttendanceInputMethod.MANUAL
    notes: str | None = None


class BulkAttendanceEntry(BaseSchema):
    entries: list[AttendanceCheckIn]


class AttendanceRecordResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    student_id: uuid.UUID
    class_id: uuid.UUID | None
    date: date
    status: AttendanceStatus
    check_in_time: datetime | None
    notes: str | None
    input_method: AttendanceInputMethod
    created_at: datetime


class AttendanceDailySummary(BaseSchema):
    date: date
    total: int
    present: int
    absent: int
    late: int
    excused: int
    sick: int
    attendance_rate: float


class LeaveRequestCreate(BaseSchema):
    tenant_id: uuid.UUID
    student_id: uuid.UUID
    start_date: date
    end_date: date
    reason: str


class LeaveRequestResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    student_id: uuid.UUID
    request_date: date
    start_date: date
    end_date: date
    reason: str
    status: LeaveRequestStatus
    approved_by_user_id: uuid.UUID | None
    approved_at: datetime | None
    created_at: datetime
