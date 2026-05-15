from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import get_current_active_user, get_tenant_user, require_roles
from app.core.database import AsyncSession, get_db
from app.domains.academics.repository import GradeRepository
from app.domains.academics.schemas import GradeResponse
from app.domains.attendance.repository import AttendanceRepository
from app.domains.attendance.schemas import AttendanceRecordResponse
from app.domains.finance.repository import InvoiceRepository
from app.domains.finance.schemas import InvoiceResponse
from app.domains.students.repository import StudentRepository
from app.domains.students.schemas import StudentCreate, StudentResponse, StudentUpdate
from app.domains.students.service import StudentService
from app.domains.users.models import User
from app.shared.base_schema import PaginatedResponse
from app.shared.enums import StudentStatus, UserRole
from app.shared.pagination import PaginationParams, get_pagination_params

router = APIRouter()


def _get_service(db: AsyncSession) -> StudentService:
    return StudentService(StudentRepository(db))


@router.get("/", response_model=PaginatedResponse[StudentResponse])
async def list_students(
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    current_user: Annotated[User, Depends(get_tenant_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = Query(default=None),
    status: StudentStatus | None = Query(default=None),
    class_id: uuid.UUID | None = Query(default=None),
) -> PaginatedResponse[StudentResponse]:
    service = _get_service(db)
    tenant_id = current_user.tenant_id
    items, total = await service.list_students(
        tenant_id=tenant_id,
        pagination=pagination,
        query=search,
        status=status,
        class_id=class_id,
    )
    return PaginatedResponse.create(
        items=[StudentResponse.model_validate(s) for s in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


@router.post("/", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student(
    data: StudentCreate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StudentResponse:
    service = _get_service(db)
    student = await service.create_student(data)
    return StudentResponse.model_validate(student)


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StudentResponse:
    service = _get_service(db)
    student = await service.get_or_404(student_id, current_user.tenant_id)
    return StudentResponse.model_validate(student)


@router.put("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: uuid.UUID,
    data: StudentUpdate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StudentResponse:
    service = _get_service(db)
    student = await service.update_student(student_id, current_user.tenant_id, data)
    return StudentResponse.model_validate(student)


@router.delete("/{student_id}", status_code=status.HTTP_200_OK)
async def delete_student(
    student_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    service = _get_service(db)
    await service.delete_student(student_id, current_user.tenant_id)


@router.get("/{student_id}/attendance", response_model=list[AttendanceRecordResponse])
async def get_student_attendance(
    student_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AttendanceRecordResponse]:
    repo = AttendanceRepository(db)
    records = await repo.list_by_student(student_id, current_user.tenant_id)
    return [AttendanceRecordResponse.model_validate(r) for r in records]


@router.get("/{student_id}/grades", response_model=list[GradeResponse])
async def get_student_grades(
    student_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[GradeResponse]:
    repo = GradeRepository(db)
    grades = await repo.list_by_student(student_id, current_user.tenant_id)
    return [GradeResponse.model_validate(g) for g in grades]


@router.get("/{student_id}/invoices", response_model=list[InvoiceResponse])
async def get_student_invoices(
    student_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[InvoiceResponse]:
    repo = InvoiceRepository(db)
    invoices = await repo.list_by_student(student_id, current_user.tenant_id)
    return [InvoiceResponse.model_validate(i) for i in invoices]


@router.get("/{student_id}/qr-code")
async def get_student_qr_code(
    student_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    service = _get_service(db)
    png_bytes = await service.generate_qr_code(student_id, current_user.tenant_id)
    return Response(content=png_bytes, media_type="image/png")
