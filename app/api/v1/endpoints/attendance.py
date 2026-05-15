from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_active_user, require_roles
from app.core.database import AsyncSession, get_db
from app.domains.attendance.repository import AttendanceRepository, LeaveRequestRepository
from app.domains.attendance.schemas import (
    AttendanceCheckIn,
    AttendanceDailySummary,
    AttendanceRecordResponse,
    BulkAttendanceEntry,
    LeaveRequestCreate,
    LeaveRequestResponse,
)
from app.domains.attendance.service import AttendanceService
from app.domains.users.models import User
from app.shared.enums import UserRole

router = APIRouter()


def _get_service(db: AsyncSession) -> AttendanceService:
    return AttendanceService(
        attendance_repo=AttendanceRepository(db),
        leave_repo=LeaveRequestRepository(db),
    )


@router.post("/check-in", response_model=AttendanceRecordResponse, status_code=status.HTTP_201_CREATED)
async def check_in(
    data: AttendanceCheckIn,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AttendanceRecordResponse:
    service = _get_service(db)
    record = await service.check_in(data, recorded_by_user_id=current_user.id)
    return AttendanceRecordResponse.model_validate(record)


@router.post("/bulk", response_model=list[AttendanceRecordResponse], status_code=status.HTTP_201_CREATED)
async def bulk_attendance(
    data: BulkAttendanceEntry,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TEACHER, UserRole.ADMIN_STAFF, UserRole.TENANT_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AttendanceRecordResponse]:
    service = _get_service(db)
    records = await service.bulk_check_in(data, recorded_by_user_id=current_user.id)
    return [AttendanceRecordResponse.model_validate(r) for r in records]


@router.get("/", response_model=list[AttendanceRecordResponse])
async def list_attendance(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    record_date: date = Query(default=None),
    class_id: uuid.UUID | None = Query(default=None),
) -> list[AttendanceRecordResponse]:
    service = _get_service(db)
    if record_date is None:
        record_date = date.today()
    records = await service.attendance_repo.list_by_date_and_class(
        tenant_id=current_user.tenant_id,
        record_date=record_date,
        class_id=class_id,
    )
    return [AttendanceRecordResponse.model_validate(r) for r in records]


@router.get("/report/daily", response_model=AttendanceDailySummary)
async def daily_report(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    record_date: date = Query(default=None),
    class_id: uuid.UUID | None = Query(default=None),
) -> AttendanceDailySummary:
    service = _get_service(db)
    if record_date is None:
        record_date = date.today()
    return await service.get_daily_summary(current_user.tenant_id, record_date, class_id)


@router.post("/leave-request", response_model=LeaveRequestResponse, status_code=status.HTTP_201_CREATED)
async def submit_leave_request(
    data: LeaveRequestCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LeaveRequestResponse:
    service = _get_service(db)
    leave = await service.submit_leave_request(data)
    return LeaveRequestResponse.model_validate(leave)


@router.put("/leave-request/{leave_id}/approve", response_model=LeaveRequestResponse)
async def approve_leave(
    leave_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TEACHER, UserRole.ADMIN_STAFF, UserRole.TENANT_ADMIN, UserRole.BOARDING_SUPERVISOR
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LeaveRequestResponse:
    service = _get_service(db)
    leave = await service.approve_leave(leave_id, current_user.tenant_id, current_user.id)
    return LeaveRequestResponse.model_validate(leave)


@router.put("/leave-request/{leave_id}/reject", response_model=LeaveRequestResponse)
async def reject_leave(
    leave_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TEACHER, UserRole.ADMIN_STAFF, UserRole.TENANT_ADMIN, UserRole.BOARDING_SUPERVISOR
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LeaveRequestResponse:
    service = _get_service(db)
    leave = await service.reject_leave(leave_id, current_user.tenant_id)
    return LeaveRequestResponse.model_validate(leave)
