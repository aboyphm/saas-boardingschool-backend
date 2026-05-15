from __future__ import annotations

import uuid

from app.domains.notifications.models import NotificationLog
from app.domains.notifications.repository import (
    NotificationLogRepository,
    NotificationTemplateRepository,
)
from app.domains.notifications.schemas import SendNotificationRequest
from app.shared.enums import NotificationStatus


class NotificationService:
    def __init__(
        self,
        template_repo: NotificationTemplateRepository,
        log_repo: NotificationLogRepository,
    ) -> None:
        self.template_repo = template_repo
        self.log_repo = log_repo

    async def send(self, request: SendNotificationRequest) -> NotificationLog:
        """
        Persist a notification log entry and enqueue the delivery task.

        Actual delivery is handled by Celery workers to avoid blocking the
        request lifecycle.
        """
        log = NotificationLog(
            tenant_id=request.tenant_id,
            recipient_user_id=request.recipient_user_id,
            channel=request.channel,
            subject=request.subject,
            body=request.body,
            status=NotificationStatus.PENDING,
        )
        self.log_repo.session.add(log)
        await self.log_repo.session.flush()
        await self.log_repo.session.refresh(log)

        # Enqueue async delivery
        from app.infrastructure.queue.tasks.notification_tasks import send_bulk_notification
        send_bulk_notification.delay([str(log.id)])

        return log

    async def list_for_user(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> list[NotificationLog]:
        return await self.log_repo.list_by_user(user_id, tenant_id)
