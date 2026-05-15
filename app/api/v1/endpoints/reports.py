from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_active_user, require_roles
from app.core.database import AsyncSession, get_db
from app.domains.reports.schemas import (
    AttendanceReportRequest,
    AttendanceReportResponse,
    FinanceReportRequest,
    FinanceReportResponse,
)
from app.domains.reports.service import ReportService
from app.domains.users.models import User
from app.shared.enums import UserRole

router = APIRouter()


@router.post("/attendance", response_model=AttendanceReportResponse)
async def attendance_report(
    data: AttendanceReportRequest,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.TEACHER,
        UserRole.OWNER, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AttendanceReportResponse:
    """Generate a per-student attendance summary for the requested date range."""
    service = ReportService(db)
    return await service.generate_attendance_report(data)


@router.post("/finance", response_model=FinanceReportResponse)
async def finance_report(
    data: FinanceReportRequest,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.FINANCE_STAFF, UserRole.OWNER, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FinanceReportResponse:
    """Generate an invoice and payment summary for the requested period."""
    service = ReportService(db)
    return await service.generate_finance_report(data)
