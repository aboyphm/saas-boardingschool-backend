from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_active_user, require_roles
from app.core.database import AsyncSession, get_db
from app.domains.teachers.repository import TeacherRepository
from app.domains.teachers.schemas import TeacherCreate, TeacherResponse, TeacherUpdate
from app.domains.teachers.service import TeacherService
from app.domains.users.models import User
from app.domains.users.repository import UserRepository
from app.shared.base_schema import PaginatedResponse
from app.shared.enums import UserRole
from app.shared.pagination import PaginationParams, get_pagination_params

router = APIRouter()


def _get_service(db: AsyncSession) -> TeacherService:
    return TeacherService(TeacherRepository(db), UserRepository(db))


def _tenant(user: User) -> uuid.UUID:
    if user.tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenant context.")
    return user.tenant_id


@router.get("/", response_model=PaginatedResponse[TeacherResponse])
async def list_teachers(
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = Query(default=None),
) -> PaginatedResponse[TeacherResponse]:
    service = _get_service(db)
    items, total = await service.list_teachers(
        tenant_id=_tenant(current_user),
        pagination=pagination,
        query=search,
    )
    return PaginatedResponse.create(
        items=[TeacherResponse.model_validate(t) for t in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


@router.post("/", response_model=TeacherResponse, status_code=status.HTTP_201_CREATED)
async def create_teacher(
    data: TeacherCreate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeacherResponse:
    service = _get_service(db)
    teacher = await service.create_teacher(data)
    return TeacherResponse.model_validate(teacher)


@router.get("/{teacher_id}", response_model=TeacherResponse)
async def get_teacher(
    teacher_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeacherResponse:
    service = _get_service(db)
    teacher = await service.get_or_404(teacher_id, _tenant(current_user))
    return TeacherResponse.model_validate(teacher)


@router.put("/{teacher_id}", response_model=TeacherResponse)
async def update_teacher(
    teacher_id: uuid.UUID,
    data: TeacherUpdate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeacherResponse:
    service = _get_service(db)
    teacher = await service.update_teacher(teacher_id, _tenant(current_user), data)
    return TeacherResponse.model_validate(teacher)


@router.delete("/{teacher_id}", status_code=status.HTTP_200_OK)
async def delete_teacher(
    teacher_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    service = _get_service(db)
    await service.delete_teacher(teacher_id, _tenant(current_user))
