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


@router.get("", response_model=list[AttendanceRecordResponse])
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
    # For STUDENT: override student_id with own record — never trust client
    if current_user.role == UserRole.STUDENT:
        from app.domains.students.repository import StudentRepository
        from app.core.exceptions import ForbiddenError
        if current_user.tenant_id is None:
            raise ForbiddenError("No tenant context for this account.")
        repo = StudentRepository(db)
        student = await repo.get_by_user_id(current_user.id, current_user.tenant_id)
        if student is None:
            raise ForbiddenError("No student record found for this account.")
        data.student_id = student.id
    elif current_user.role == UserRole.PARENT:
        # PARENT: verify the submitted student_id is one of their children
        from app.domains.students.repository import StudentRepository
        from app.core.exceptions import ForbiddenError
        repo = StudentRepository(db)
        if current_user.tenant_id is None:
            raise ForbiddenError("No tenant context.")
        children = await repo.list_by_parent_user_id(current_user.id, current_user.tenant_id)
        child_ids = {c.id for c in children}
        if data.student_id not in child_ids:
            raise ForbiddenError("You can only submit leave requests for your own children.")
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


@router.get("/leave-requests", response_model=list[LeaveRequestResponse])
async def list_leave_requests(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = Query(default=None),
) -> list[LeaveRequestResponse]:
    if current_user.tenant_id is None:
        return []
    service = _get_service(db)
    from app.shared.enums import LeaveRequestStatus
    status_enum = LeaveRequestStatus(status) if status else None
    requests = await service.list_leave_requests(current_user.tenant_id, status_enum)
    return [LeaveRequestResponse.model_validate(r) for r in requests]
