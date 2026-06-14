from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_active_user, require_roles
from app.core.database import AsyncSession, get_db
from app.core.exceptions import ForbiddenError
from app.domains.admissions.repository import AdmissionBatchRepository, AdmissionRepository
from app.domains.admissions.schemas import (
    AdmissionBatchCreate, AdmissionBatchResponse, AdmissionBatchUpdate,
    AdmissionCreate, AdmissionResponse, AdmissionStatsResponse, ReviewRequest,
)
from app.domains.admissions.service import AdmissionService
from app.domains.users.models import User
from app.shared.enums import AdmissionStatus, UserRole

router = APIRouter()

ADMIN_ROLES = (UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN)


def _tid(user: User) -> uuid.UUID:
    if user.tenant_id is None:
        raise ForbiddenError("A tenant context is required.")
    return user.tenant_id


def _get_service(db: AsyncSession) -> AdmissionService:
    return AdmissionService(
        batch_repo=AdmissionBatchRepository(db),
        admission_repo=AdmissionRepository(db),
    )


# ── Batches ───────────────────────────────────────────────────────────────────
@router.get("/batches", response_model=list[AdmissionBatchResponse])
async def list_batches(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AdmissionBatchResponse]:
    service = _get_service(db)
    batches = await service.list_batches(_tid(current_user))
    return [AdmissionBatchResponse.model_validate(b) for b in batches]


@router.post("/batches", response_model=AdmissionBatchResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    data: AdmissionBatchCreate,
    current_user: Annotated[User, Depends(require_roles(*ADMIN_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdmissionBatchResponse:
    service = _get_service(db)
    batch = await service.create_batch(data, _tid(current_user))
    return AdmissionBatchResponse.model_validate(batch)


@router.put("/batches/{batch_id}", response_model=AdmissionBatchResponse)
async def update_batch(
    batch_id: uuid.UUID,
    data: AdmissionBatchUpdate,
    current_user: Annotated[User, Depends(require_roles(*ADMIN_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdmissionBatchResponse:
    service = _get_service(db)
    batch = await service.update_batch(batch_id, data, _tid(current_user))
    return AdmissionBatchResponse.model_validate(batch)


@router.delete("/batches/{batch_id}", status_code=status.HTTP_200_OK)
async def delete_batch(
    batch_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(*ADMIN_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _get_service(db)
    await service.delete_batch(batch_id, _tid(current_user))
    return {"ok": True}


# ── Applications ──────────────────────────────────────────────────────────────
@router.get("/applications", response_model=list[AdmissionResponse])
async def list_applications(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    batch_id: uuid.UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[AdmissionResponse]:
    service = _get_service(db)
    status_enum = AdmissionStatus(status_filter) if status_filter else None
    apps = await service.list_applications(_tid(current_user), batch_id, status_enum)
    return [AdmissionResponse.model_validate(a) for a in apps]


@router.post("/applications", response_model=AdmissionResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    data: AdmissionCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdmissionResponse:
    service = _get_service(db)
    app = await service.create_application(data, _tid(current_user))
    return AdmissionResponse.model_validate(app)


@router.put("/applications/{admission_id}/review", response_model=AdmissionResponse)
async def review_application(
    admission_id: uuid.UUID,
    data: ReviewRequest,
    current_user: Annotated[User, Depends(require_roles(*ADMIN_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdmissionResponse:
    service = _get_service(db)
    app = await service.review_application(
        admission_id, data, current_user.id, _tid(current_user)
    )
    return AdmissionResponse.model_validate(app)


@router.get("/stats", response_model=AdmissionStatsResponse)
async def get_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    batch_id: uuid.UUID | None = Query(default=None),
) -> AdmissionStatsResponse:
    service = _get_service(db)
    return await service.get_stats(_tid(current_user), batch_id)
