from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from app.core.exceptions import NotFoundError
from app.domains.attendance.models import AttendanceRecord, LeaveRequest
from app.domains.attendance.repository import AttendanceRepository, LeaveRequestRepository
from app.domains.attendance.schemas import (
    AttendanceCheckIn,
    AttendanceDailySummary,
    BulkAttendanceEntry,
    LeaveRequestCreate,
)
from app.shared.enums import AttendanceStatus, LeaveRequestStatus


class AttendanceService:
    def __init__(
        self,
        attendance_repo: AttendanceRepository,
        leave_repo: LeaveRequestRepository,
    ) -> None:
        self.attendance_repo = attendance_repo
        self.leave_repo = leave_repo

    async def check_in(
        self,
        data: AttendanceCheckIn,
        recorded_by_user_id: uuid.UUID | None = None,
    ) -> AttendanceRecord:
        record = AttendanceRecord(
            tenant_id=data.tenant_id,
            student_id=data.student_id,
            class_id=data.class_id,
            date=data.date,
            status=data.status,
            notes=data.notes,
            input_method=data.input_method,
            recorded_by_user_id=recorded_by_user_id,
            check_in_time=datetime.now(UTC),
        )
        self.attendance_repo.session.add(record)
        await self.attendance_repo.session.flush()
        await self.attendance_repo.session.refresh(record)
        return record

    async def bulk_check_in(
        self,
        data: BulkAttendanceEntry,
        recorded_by_user_id: uuid.UUID | None = None,
    ) -> list[AttendanceRecord]:
        records = []
        for entry in data.entries:
            record = AttendanceRecord(
                tenant_id=entry.tenant_id,
                student_id=entry.student_id,
                class_id=entry.class_id,
                date=entry.date,
                status=entry.status,
                notes=entry.notes,
                input_method=entry.input_method,
                recorded_by_user_id=recorded_by_user_id,
                check_in_time=datetime.now(UTC),
            )
            self.attendance_repo.session.add(record)
            records.append(record)
        await self.attendance_repo.session.flush()
        for record in records:
            await self.attendance_repo.session.refresh(record)
        return records

    async def get_daily_summary(
        self,
        tenant_id: uuid.UUID,
        record_date: date,
        class_id: uuid.UUID | None = None,
    ) -> AttendanceDailySummary:
        counts = await self.attendance_repo.daily_summary(tenant_id, record_date, class_id)
        total = sum(counts.values())
        present = counts.get(AttendanceStatus.PRESENT, 0)
        rate = (present / total * 100) if total > 0 else 0.0
        return AttendanceDailySummary(
            date=record_date,
            total=total,
            present=present,
            absent=counts.get(AttendanceStatus.ABSENT, 0),
            late=counts.get(AttendanceStatus.LATE, 0),
            excused=counts.get(AttendanceStatus.EXCUSED, 0),
            sick=counts.get(AttendanceStatus.SICK, 0),
            attendance_rate=round(rate, 2),
        )

    async def submit_leave_request(self, data: LeaveRequestCreate) -> LeaveRequest:
        leave = LeaveRequest(
            tenant_id=data.tenant_id,
            student_id=data.student_id,
            request_date=date.today(),
            start_date=data.start_date,
            end_date=data.end_date,
            reason=data.reason,
            status=LeaveRequestStatus.PENDING,
        )
        self.leave_repo.session.add(leave)
        await self.leave_repo.session.flush()
        await self.leave_repo.session.refresh(leave)
        return leave

    async def approve_leave(
        self, leave_id: uuid.UUID, tenant_id: uuid.UUID, approved_by: uuid.UUID
    ) -> LeaveRequest:
        leave = await self.leave_repo.get_by_tenant(leave_id, tenant_id)
        if leave is None:
            raise NotFoundError("Leave request not found.")
        leave.status = LeaveRequestStatus.APPROVED
        leave.approved_by_user_id = approved_by
        leave.approved_at = datetime.now(UTC)
        self.leave_repo.session.add(leave)
        await self.leave_repo.session.flush()
        await self.leave_repo.session.refresh(leave)
        return leave

    async def reject_leave(
        self, leave_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> LeaveRequest:
        leave = await self.leave_repo.get_by_tenant(leave_id, tenant_id)
        if leave is None:
            raise NotFoundError("Leave request not found.")
        leave.status = LeaveRequestStatus.REJECTED
        self.leave_repo.session.add(leave)
        await self.leave_repo.session.flush()
        await self.leave_repo.session.refresh(leave)
        return leave
