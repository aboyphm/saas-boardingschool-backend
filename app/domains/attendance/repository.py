from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.attendance.models import AttendanceRecord, LeaveRequest
from app.domains.attendance.schemas import AttendanceCheckIn
from app.shared.base_repository import BaseRepository
from app.shared.enums import AttendanceStatus, LeaveRequestStatus


class AttendanceRepository(BaseRepository[AttendanceRecord, AttendanceCheckIn, AttendanceCheckIn]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AttendanceRecord, session)

    async def list_by_date_and_class(
        self,
        tenant_id: uuid.UUID,
        record_date: date,
        class_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[AttendanceRecord]:
        stmt = (
            select(AttendanceRecord)
            .where(
                AttendanceRecord.tenant_id == tenant_id,
                AttendanceRecord.date == record_date,
            )
        )
        if class_id is not None:
            stmt = stmt.where(AttendanceRecord.class_id == class_id)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_student(
        self,
        student_id: uuid.UUID,
        tenant_id: uuid.UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[AttendanceRecord]:
        stmt = (
            select(AttendanceRecord)
            .where(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.tenant_id == tenant_id,
            )
        )
        if start_date:
            stmt = stmt.where(AttendanceRecord.date >= start_date)
        if end_date:
            stmt = stmt.where(AttendanceRecord.date <= end_date)
        stmt = stmt.order_by(AttendanceRecord.date.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def daily_summary(
        self, tenant_id: uuid.UUID, record_date: date, class_id: uuid.UUID | None = None
    ) -> dict[str, int]:
        """Return per-status counts for a given day."""
        stmt = (
            select(AttendanceRecord.status, func.count().label("cnt"))
            .where(
                AttendanceRecord.tenant_id == tenant_id,
                AttendanceRecord.date == record_date,
            )
            .group_by(AttendanceRecord.status)
        )
        if class_id is not None:
            stmt = stmt.where(AttendanceRecord.class_id == class_id)
        result = await self.session.execute(stmt)
        return {row.status: row.cnt for row in result.all()}


class LeaveRequestRepository(BaseRepository[LeaveRequest, dict, dict]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(LeaveRequest, session)

    async def list_pending(self, tenant_id: uuid.UUID) -> list[LeaveRequest]:
        stmt = (
            select(LeaveRequest)
            .where(
                LeaveRequest.tenant_id == tenant_id,
                LeaveRequest.status == LeaveRequestStatus.PENDING,
            )
            .order_by(LeaveRequest.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
