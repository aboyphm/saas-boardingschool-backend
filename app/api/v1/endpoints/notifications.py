from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_active_user
from app.core.database import AsyncSession, get_db
from app.domains.notifications.repository import NotificationLogRepository, NotificationTemplateRepository
from app.domains.notifications.schemas import (
    NotificationLogResponse,
    SendNotificationRequest,
)
from app.domains.notifications.service import NotificationService
from app.domains.users.models import User

router = APIRouter()


def _get_service(db: AsyncSession) -> NotificationService:
    return NotificationService(
        template_repo=NotificationTemplateRepository(db),
        log_repo=NotificationLogRepository(db),
    )


@router.post("/send", response_model=NotificationLogResponse, status_code=status.HTTP_201_CREATED)
async def send_notification(
    data: SendNotificationRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationLogResponse:
    service = _get_service(db)
    log = await service.send(data)
    return NotificationLogResponse.model_validate(log)


@router.get("/", response_model=list[NotificationLogResponse])
async def list_my_notifications(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[NotificationLogResponse]:
    service = _get_service(db)
    logs = await service.list_for_user(current_user.id, current_user.tenant_id)
    return [NotificationLogResponse.model_validate(l) for l in logs]
