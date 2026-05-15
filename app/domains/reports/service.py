from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.attendance.models import AttendanceRecord
from app.domains.finance.models import Invoice
from app.domains.reports.schemas import (
    AttendanceReportRequest,
    AttendanceReportResponse,
    AttendanceReportRow,
    FinanceReportRequest,
    FinanceReportResponse,
    StudentProgressRequest,
    StudentProgressResponse,
)
from app.domains.students.models import Student
from app.shared.enums import AttendanceStatus, InvoiceStatus


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def generate_attendance_report(
        self, request: AttendanceReportRequest
    ) -> AttendanceReportResponse:
        """Aggregate per-student attendance counts across a date range."""
        # Fetch students in the tenant (optionally filtered by class)
        student_stmt = select(Student).where(
            Student.tenant_id == request.tenant_id,
            Student.is_deleted.is_(False),
        )
        if request.student_id:
            student_stmt = student_stmt.where(Student.id == request.student_id)
        elif request.class_id:
            student_stmt = student_stmt.where(Student.class_id == request.class_id)

        student_result = await self.session.execute(student_stmt)
        students = student_result.scalars().all()

        rows: list[AttendanceReportRow] = []
        for student in students:
            counts_stmt = (
                select(AttendanceRecord.status, func.count().label("cnt"))
                .where(
                    AttendanceRecord.student_id == student.id,
                    AttendanceRecord.tenant_id == request.tenant_id,
                    AttendanceRecord.date >= request.start_date,
                    AttendanceRecord.date <= request.end_date,
                )
                .group_by(AttendanceRecord.status)
            )
            counts_result = await self.session.execute(counts_stmt)
            counts = {row.status: row.cnt for row in counts_result.all()}

            present = counts.get(AttendanceStatus.PRESENT, 0)
            absent = counts.get(AttendanceStatus.ABSENT, 0)
            late = counts.get(AttendanceStatus.LATE, 0)
            excused = counts.get(AttendanceStatus.EXCUSED, 0)
            sick = counts.get(AttendanceStatus.SICK, 0)
            total = present + absent + late + excused + sick
            rate = round((present / total * 100), 2) if total > 0 else 0.0

            rows.append(AttendanceReportRow(
                student_id=student.id,
                student_name=student.full_name,
                nis=student.nis,
                total_days=total,
                present=present,
                absent=absent,
                late=late,
                excused=excused,
                sick=sick,
                attendance_rate=rate,
            ))

        return AttendanceReportResponse(
            tenant_id=request.tenant_id,
            start_date=request.start_date,
            end_date=request.end_date,
            rows=rows,
            summary={"total_students": len(rows)},
        )

    async def generate_finance_report(
        self, request: FinanceReportRequest
    ) -> FinanceReportResponse:
        """Aggregate invoice totals for the requested period."""
        stmt = (
            select(
                Invoice.status,
                func.count().label("count"),
                func.coalesce(func.sum(Invoice.total_amount), 0).label("total"),
            )
            .where(Invoice.tenant_id == request.tenant_id)
            .group_by(Invoice.status)
        )
        result = await self.session.execute(stmt)
        stats = {row.status: {"count": row.count, "total": float(row.total)} for row in result.all()}

        invoiced = sum(v["total"] for v in stats.values())
        collected = stats.get(InvoiceStatus.PAID, {}).get("total", 0.0)
        outstanding = stats.get(InvoiceStatus.OVERDUE, {}).get("total", 0.0)
        rate = round((collected / invoiced * 100), 2) if invoiced > 0 else 0.0
        period = f"{request.year}" + (f"-{request.month:02d}" if request.month else "")

        return FinanceReportResponse(
            tenant_id=request.tenant_id,
            period=period,
            total_invoiced=invoiced,
            total_collected=collected,
            total_outstanding=outstanding,
            collection_rate=rate,
            by_month=[],
        )
