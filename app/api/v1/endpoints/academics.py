from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_active_user, require_roles
from app.core.database import AsyncSession, get_db
from app.core.exceptions import ForbiddenError


def _tid(user: User) -> uuid.UUID:
    """Narrow ``user.tenant_id`` from ``UUID | None`` → ``UUID``.

    SUPER_ADMIN accounts have ``tenant_id=None`` and must not reach
    tenant-scoped academics endpoints without an explicit tenant context.
    All other roles always have a tenant_id set.
    """
    if user.tenant_id is None:
        raise ForbiddenError("A tenant context is required for this endpoint.")
    return user.tenant_id
from app.domains.academics.repository import (
    AcademicYearRepository,
    ClassEnrollmentRepository,
    ClassRoomRepository,
    GradeCurriculumRepository,
    GradeRepository,
    ScheduleSlotRepository,
    SchoolEventRepository,
    SubjectRepository,
)
from app.domains.academics.schemas import (
    AcademicYearCreate,
    AcademicYearResponse,
    AcademicYearUpdate,
    ClassEnrollmentResponse,
    ClassGradeMatrixResponse,
    ClassRoomCreate,
    ClassRoomResponse,
    ClassRoomUpdate,
    EnrollStudentRequest,
    GradeBatchRequest,
    GradeCurriculumResponse,
    GradeCurriculumRow,
    GradeCurriculumUpsert,
    GradeCreate,
    GradeResponse,
    ScheduleSlotCreate,
    ScheduleSlotResponse,
    ScheduleSlotUpdate,
    SchoolEventCreate,
    SchoolEventResponse,
    SchoolEventUpdate,
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
        enrollment_repo=ClassEnrollmentRepository(db),
        event_repo=SchoolEventRepository(db),
        slot_repo=ScheduleSlotRepository(db),
        curriculum_repo=GradeCurriculumRepository(db),
    )


# ─── Academic years ───────────────────────────────────────────────────────────
@router.get("/years", response_model=list[AcademicYearResponse])
async def list_academic_years(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AcademicYearResponse]:
    service = _get_service(db)
    years = await service.list_years(_tid(current_user))
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
    data.tenant_id = _tid(current_user)
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
    classes = await service.list_classes(_tid(current_user), academic_year_id)
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
    data.tenant_id = _tid(current_user)
    classroom = await service.create_class(data)
    return ClassRoomResponse.model_validate(classroom)


# ─── Subjects ─────────────────────────────────────────────────────────────────
@router.get("/subjects", response_model=list[SubjectResponse])
async def list_subjects(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SubjectResponse]:
    service = _get_service(db)
    subjects = await service.list_subjects(_tid(current_user))
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
    data.tenant_id = _tid(current_user)
    subject = await service.create_subject(data)
    return SubjectResponse.model_validate(subject)


# ─── Grades ───────────────────────────────────────────────────────────────────
@router.post("/grades", response_model=GradeResponse, status_code=status.HTTP_201_CREATED)
async def record_grade(
    data: GradeCreate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TEACHER, UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GradeResponse:
    service = _get_service(db)
    data.tenant_id = _tid(current_user)
    grade = await service.record_grade(data)
    return GradeResponse.model_validate(grade)


# ─── Academic years: complete CRUD ────────────────────────────────────────
@router.get("/years/{year_id}", response_model=AcademicYearResponse)
async def get_academic_year(
    year_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AcademicYearResponse:
    service = _get_service(db)
    year = await service.get_year_or_404(year_id, _tid(current_user))
    return AcademicYearResponse.model_validate(year)


@router.put("/years/{year_id}", response_model=AcademicYearResponse)
async def update_academic_year(
    year_id: uuid.UUID,
    data: AcademicYearUpdate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AcademicYearResponse:
    service = _get_service(db)
    year = await service.update_year(year_id, data, _tid(current_user))
    return AcademicYearResponse.model_validate(year)


@router.delete("/years/{year_id}", status_code=status.HTTP_200_OK)
async def delete_academic_year(
    year_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _get_service(db)
    await service.delete_year(year_id, _tid(current_user))
    return {"ok": True}


# ─── Classes: complete CRUD ───────────────────────────────────────────────
@router.get("/classes/{class_id}", response_model=ClassRoomResponse)
async def get_class(
    class_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClassRoomResponse:
    service = _get_service(db)
    classroom = await service.get_class_or_404(class_id, _tid(current_user))
    return ClassRoomResponse.model_validate(classroom)


@router.put("/classes/{class_id}", response_model=ClassRoomResponse)
async def update_class(
    class_id: uuid.UUID,
    data: ClassRoomUpdate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClassRoomResponse:
    service = _get_service(db)
    classroom = await service.update_class(class_id, data, _tid(current_user))
    return ClassRoomResponse.model_validate(classroom)


@router.delete("/classes/{class_id}", status_code=status.HTTP_200_OK)
async def delete_class(
    class_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _get_service(db)
    await service.delete_class(class_id, _tid(current_user))
    return {"ok": True}


# ─── Enrollment ────────────────────────────────────────────────────────────
@router.get("/classes/{class_id}/enrollments", response_model=list[ClassEnrollmentResponse])
async def list_class_enrollments(
    class_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ClassEnrollmentResponse]:
    service = _get_service(db)
    enrollments = await service.list_class_enrollments(class_id, _tid(current_user))
    return [ClassEnrollmentResponse.model_validate(e) for e in enrollments]


@router.post("/classes/{class_id}/enrollments",
             response_model=ClassEnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll_student(
    class_id: uuid.UUID,
    data: EnrollStudentRequest,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClassEnrollmentResponse:
    service = _get_service(db)
    enrollment = await service.enroll_student(class_id, data, _tid(current_user))
    return ClassEnrollmentResponse.model_validate(enrollment)


@router.delete("/classes/{class_id}/enrollments/{student_id}", status_code=status.HTTP_200_OK)
async def remove_enrollment(
    class_id: uuid.UUID,
    student_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _get_service(db)
    await service.remove_enrollment(class_id, student_id, _tid(current_user))
    return {"ok": True}


# ─── Subjects: complete CRUD ───────────────────────────────────────────────
@router.get("/subjects/{subject_id}", response_model=SubjectResponse)
async def get_subject(
    subject_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SubjectResponse:
    service = _get_service(db)
    subject = await service.get_subject_or_404(subject_id, _tid(current_user))
    return SubjectResponse.model_validate(subject)


@router.put("/subjects/{subject_id}", response_model=SubjectResponse)
async def update_subject(
    subject_id: uuid.UUID,
    data: SubjectUpdate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SubjectResponse:
    service = _get_service(db)
    subject = await service.update_subject(subject_id, data, _tid(current_user))
    return SubjectResponse.model_validate(subject)


@router.delete("/subjects/{subject_id}", status_code=status.HTTP_200_OK)
async def delete_subject(
    subject_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _get_service(db)
    await service.delete_subject(subject_id, _tid(current_user))
    return {"ok": True}


# ─── Grade matrix + batch upsert ──────────────────────────────────────────
@router.get("/grades", response_model=ClassGradeMatrixResponse)
async def get_class_grade_matrix(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    class_id: uuid.UUID = Query(...),
    academic_year_id: uuid.UUID = Query(...),
    semester: int = Query(..., ge=1, le=2),
) -> ClassGradeMatrixResponse:
    service = _get_service(db)
    return await service.list_class_grades(
        class_id, academic_year_id, semester, _tid(current_user)
    )


@router.post("/grades/batch", status_code=status.HTTP_200_OK)
async def batch_upsert_grades(
    data: GradeBatchRequest,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TEACHER, UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _get_service(db)
    count = await service.batch_upsert_grades(data.grades, _tid(current_user))
    return {"updated": count}


# ─── School events ────────────────────────────────────────────────────────
@router.get("/events", response_model=list[SchoolEventResponse])
async def list_events(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    academic_year_id: uuid.UUID | None = Query(default=None),
) -> list[SchoolEventResponse]:
    service = _get_service(db)
    events = await service.list_events(_tid(current_user), academic_year_id)
    return [SchoolEventResponse.model_validate(e) for e in events]


@router.post("/events", response_model=SchoolEventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: SchoolEventCreate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SchoolEventResponse:
    service = _get_service(db)
    event = await service.create_event(data, _tid(current_user))
    return SchoolEventResponse.model_validate(event)


@router.put("/events/{event_id}", response_model=SchoolEventResponse)
async def update_event(
    event_id: uuid.UUID,
    data: SchoolEventUpdate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SchoolEventResponse:
    service = _get_service(db)
    event = await service.update_event(event_id, data, _tid(current_user))
    return SchoolEventResponse.model_validate(event)


@router.delete("/events/{event_id}", status_code=status.HTTP_200_OK)
async def delete_event(
    event_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _get_service(db)
    await service.delete_event(event_id, _tid(current_user))
    return {"ok": True}


# ─── Grade Curriculum ─────────────────────────────────────────────────────

@router.get("/curriculum", response_model=list[GradeCurriculumRow])
async def list_curriculum(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[GradeCurriculumRow]:
    service = _get_service(db)
    return await service.list_curriculum_matrix(_tid(current_user))


@router.post("/curriculum", response_model=GradeCurriculumResponse, status_code=status.HTTP_200_OK)
async def upsert_curriculum(
    data: GradeCurriculumUpsert,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GradeCurriculumResponse:
    service = _get_service(db)
    entry = await service.upsert_curriculum(data, _tid(current_user))
    return GradeCurriculumResponse.model_validate(entry)


@router.delete("/curriculum/{subject_id}/{grade_level}", status_code=status.HTTP_200_OK)
async def remove_curriculum(
    subject_id: uuid.UUID,
    grade_level: str,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _get_service(db)
    await service.remove_curriculum(subject_id, grade_level, _tid(current_user))
    return {"ok": True}


# ─── Timetable ────────────────────────────────────────────────────────────
@router.get("/timetable", response_model=list[ScheduleSlotResponse])
async def get_timetable(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    class_id: uuid.UUID = Query(...),
    academic_year_id: uuid.UUID = Query(...),
) -> list[ScheduleSlotResponse]:
    service = _get_service(db)
    slots = await service.list_timetable(class_id, academic_year_id, _tid(current_user))
    return [ScheduleSlotResponse.model_validate(s) for s in slots]


@router.post("/timetable", response_model=ScheduleSlotResponse, status_code=status.HTTP_201_CREATED)
async def create_slot(
    data: ScheduleSlotCreate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScheduleSlotResponse:
    service = _get_service(db)
    slot = await service.create_slot(data, _tid(current_user))
    return ScheduleSlotResponse.model_validate(slot)


@router.put("/timetable/{slot_id}", response_model=ScheduleSlotResponse)
async def update_slot(
    slot_id: uuid.UUID,
    data: ScheduleSlotUpdate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScheduleSlotResponse:
    service = _get_service(db)
    slot = await service.update_slot(slot_id, data, _tid(current_user))
    return ScheduleSlotResponse.model_validate(slot)


@router.delete("/timetable/{slot_id}", status_code=status.HTTP_200_OK)
async def delete_slot(
    slot_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _get_service(db)
    await service.delete_slot(slot_id, _tid(current_user))
    return {"ok": True}
