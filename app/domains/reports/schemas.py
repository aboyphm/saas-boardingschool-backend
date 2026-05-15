from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel

from app.shared.base_schema import BaseSchema


class AttendanceReportRequest(BaseSchema):
    tenant_id: uuid.UUID
    start_date: date
    end_date: date
    class_id: uuid.UUID | None = None
    student_id: uuid.UUID | None = None


class AttendanceReportRow(BaseSchema):
    student_id: uuid.UUID
    student_name: str
    nis: str
    total_days: int
    present: int
    absent: int
    late: int
    excused: int
    sick: int
    attendance_rate: float


class AttendanceReportResponse(BaseSchema):
    tenant_id: uuid.UUID
    start_date: date
    end_date: date
    rows: list[AttendanceReportRow]
    summary: dict


class FinanceReportRequest(BaseSchema):
    tenant_id: uuid.UUID
    year: int
    month: int | None = None


class FinanceReportResponse(BaseSchema):
    tenant_id: uuid.UUID
    period: str
    total_invoiced: float
    total_collected: float
    total_outstanding: float
    collection_rate: float
    by_month: list[dict]


class StudentProgressRequest(BaseSchema):
    tenant_id: uuid.UUID
    student_id: uuid.UUID
    academic_year_id: uuid.UUID | None = None


class StudentProgressResponse(BaseSchema):
    student_id: uuid.UUID
    student_name: str
    academic_year: str | None
    grades: list[dict]
    attendance_summary: dict
    outstanding_invoices: int
