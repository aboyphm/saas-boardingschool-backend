from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_active_user, require_roles
from app.core.database import AsyncSession, get_db
from app.domains.academics.repository import (
    AcademicYearRepository,
    ClassRoomRepository,
    GradeRepository,
    SubjectRepository,
)
from app.domains.academics.schemas import (
    AcademicYearCreate,
    AcademicYearResponse,
    ClassRoomCreate,
    ClassRoomResponse,
    ClassRoomUpdate,
    GradeCreate,
    GradeResponse,
    SubjectCreate,
    SubjectResponse,
    SubjectUpdate,
)
from app.domains.academics.service import AcademicsService
from app.domains.users.models import User
from app.shared.enums import UserRole

router = APIRouter()


def _get_service(db: AsyncSession) -> AcademicsService:
    return AcademicsService(
        year_repo=AcademicYearRepository(db),
        class_repo=ClassRoomRepository(db),
        subject_repo=SubjectRepository(db),
        grade_repo=GradeRepository(db),
    )


# ─── Academic years ───────────────────────────────────────────────────────────
@router.get("/years", response_model=list[AcademicYearResponse])
async def list_academic_years(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AcademicYearResponse]:
    service = _get_service(db)
    years = await service.list_years(current_user.tenant_id)
    return [AcademicYearResponse.model_validate(y) for y in years]


@router.post("/years", response_model=AcademicYearResponse, status_code=status.HTTP_201_CREATED)
async def create_academic_year(
    data: AcademicYearCreate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AcademicYearResponse:
    service = _get_service(db)
    year = await service.create_year(data)
    return AcademicYearResponse.model_validate(year)


# ─── Classes ──────────────────────────────────────────────────────────────────
@router.get("/classes", response_model=list[ClassRoomResponse])
async def list_classes(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    academic_year_id: uuid.UUID | None = Query(default=None),
) -> list[ClassRoomResponse]:
    service = _get_service(db)
    classes = await service.list_classes(current_user.tenant_id, academic_year_id)
    return [ClassRoomResponse.model_validate(c) for c in classes]


@router.post("/classes", response_model=ClassRoomResponse, status_code=status.HTTP_201_CREATED)
async def create_class(
    data: ClassRoomCreate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClassRoomResponse:
    service = _get_service(db)
    classroom = await service.create_class(data)
    return ClassRoomResponse.model_validate(classroom)


# ─── Subjects ─────────────────────────────────────────────────────────────────
@router.get("/subjects", response_model=list[SubjectResponse])
async def list_subjects(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SubjectResponse]:
    service = _get_service(db)
    subjects = await service.list_subjects(current_user.tenant_id)
    return [SubjectResponse.model_validate(s) for s in subjects]


@router.post("/subjects", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def create_subject(
    data: SubjectCreate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SubjectResponse:
    service = _get_service(db)
    subject = await service.create_subject(data)
    return SubjectResponse.model_validate(subject)


# ─── Grades ───────────────────────────────────────────────────────────────────
@router.post("/grades", response_model=GradeResponse, status_code=status.HTTP_201_CREATED)
async def record_grade(
    data: GradeCreate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TEACHER, UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GradeResponse:
    service = _get_service(db)
    grade = await service.record_grade(data)
    return GradeResponse.model_validate(grade)
