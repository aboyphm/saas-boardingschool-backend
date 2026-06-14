from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_active_user, require_roles
from app.core.database import AsyncSession, get_db
from app.domains.notifications.repository import NotificationLogRepository, NotificationTemplateRepository
from app.domains.notifications.schemas import (
    NotificationLogResponse,
    NotificationTemplateCreate,
    NotificationTemplateResponse,
    SendNotificationRequest,
)
from app.domains.notifications.service import NotificationService
from app.domains.users.models import User
from app.shared.enums import UserRole

WRITE_ROLES = (UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN)


def _tid(user: User) -> uuid.UUID:
    if user.tenant_id is None:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("A tenant context is required.")
    return user.tenant_id

router = APIRouter()


def _get_service(db: AsyncSession) -> NotificationService:
    return NotificationService(
        template_repo=NotificationTemplateRepository(db),
        log_repo=NotificationLogRepository(db),
    )


@router.post("/send", response_model=NotificationLogResponse, status_code=status.HTTP_201_CREATED)
async def send_notification(
    data: SendNotificationRequest,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.TEACHER, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationLogResponse:
    service = _get_service(db)
    log = await service.send(data)
    return NotificationLogResponse.model_validate(log)


@router.get("", response_model=list[NotificationLogResponse])
async def list_my_notifications(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[NotificationLogResponse]:
    service = _get_service(db)
    logs = await service.list_for_user(current_user.id, current_user.tenant_id)
    return [NotificationLogResponse.model_validate(l) for l in logs]


@router.get("/templates", response_model=list[NotificationTemplateResponse])
async def list_templates(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[NotificationTemplateResponse]:
    service = _get_service(db)
    templates = await service.list_templates(_tid(current_user))
    return [NotificationTemplateResponse.model_validate(t) for t in templates]


@router.post("/templates", response_model=NotificationTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: NotificationTemplateCreate,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationTemplateResponse:
    service = _get_service(db)
    template = await service.create_template(data, _tid(current_user))
    return NotificationTemplateResponse.model_validate(template)


@router.put("/templates/{template_id}", response_model=NotificationTemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    data: NotificationTemplateCreate,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationTemplateResponse:
    service = _get_service(db)
    template = await service.update_template(template_id, data, _tid(current_user))
    return NotificationTemplateResponse.model_validate(template)


@router.delete("/templates/{template_id}", status_code=status.HTTP_200_OK)
async def delete_template(
    template_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _get_service(db)
    await service.delete_template(template_id, _tid(current_user))
    return {"ok": True}
