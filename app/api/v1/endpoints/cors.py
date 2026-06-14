from __future__ import annotations
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, status
from app.api.deps import require_roles
from app.core.database import AsyncSession, get_db
from app.core.exceptions import ConflictError, NotFoundError
from app.core.cors_registry import add_origin, remove_origin
from app.domains.cors.models import CorsOrigin
from app.domains.cors.repository import CorsOriginRepository
from app.domains.cors.schemas import CorsOriginCreate, CorsOriginResponse
from app.domains.users.models import User
from app.shared.enums import UserRole

router = APIRouter()


def _repo(db: AsyncSession) -> CorsOriginRepository:
    return CorsOriginRepository(db)


@router.get("", response_model=list[CorsOriginResponse])
async def list_cors_origins(
    current_user: Annotated[User, Depends(require_roles(UserRole.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CorsOriginResponse]:
    return [CorsOriginResponse.model_validate(e) for e in await _repo(db).list_all()]


@router.post("", response_model=CorsOriginResponse, status_code=status.HTTP_201_CREATED)
async def create_cors_origin(
    data: CorsOriginCreate,
    current_user: Annotated[User, Depends(require_roles(UserRole.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CorsOriginResponse:
    repo = _repo(db)
    if await repo.get_by_origin(data.origin):
        raise ConflictError(f"Origin '{data.origin}' already exists.")
    entry = CorsOrigin(origin=data.origin, description=data.description, is_active=data.is_active)
    repo.session.add(entry)
    await repo.session.flush()
    await repo.session.refresh(entry)
    if entry.is_active:
        add_origin(entry.origin)
    return CorsOriginResponse.model_validate(entry)


@router.delete("/{origin_id}", status_code=status.HTTP_200_OK)
async def delete_cors_origin(
    origin_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(UserRole.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    repo = _repo(db)
    entry = await repo.get(origin_id)
    if entry is None:
        raise NotFoundError("CORS origin not found.")
    remove_origin(entry.origin)
    await repo.session.delete(entry)
    await repo.session.flush()
    return {"ok": True}


@router.patch("/{origin_id}/toggle", response_model=CorsOriginResponse)
async def toggle_cors_origin(
    origin_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(UserRole.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CorsOriginResponse:
    repo = _repo(db)
    entry = await repo.get(origin_id)
    if entry is None:
        raise NotFoundError("CORS origin not found.")
    entry.is_active = not entry.is_active
    if entry.is_active:
        add_origin(entry.origin)
    else:
        remove_origin(entry.origin)
    await repo.session.flush()
    await repo.session.refresh(entry)
    return CorsOriginResponse.model_validate(entry)
