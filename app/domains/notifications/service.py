from __future__ import annotations

import uuid

from app.domains.notifications.models import NotificationLog, NotificationTemplate
from app.domains.notifications.repository import (
    NotificationLogRepository,
    NotificationTemplateRepository,
)
from app.domains.notifications.schemas import NotificationTemplateCreate, SendNotificationRequest
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

    # ── Templates ─────────────────────────────────────────────────────────────
    async def list_templates(
        self, tenant_id: uuid.UUID
    ) -> list[NotificationTemplate]:
        return await self.template_repo.list_by_tenant(tenant_id)

    async def create_template(
        self, data: "NotificationTemplateCreate", tenant_id: uuid.UUID
    ) -> NotificationTemplate:
        template = NotificationTemplate(
            tenant_id=tenant_id,
            name=data.name,
            channel=data.channel,
            subject=data.subject,
            body_template=data.body_template,
            variables=data.variables,
        )
        self.template_repo.session.add(template)
        await self.template_repo.session.flush()
        await self.template_repo.session.refresh(template)
        return template

    async def update_template(
        self,
        template_id: uuid.UUID,
        data: NotificationTemplateCreate,
        tenant_id: uuid.UUID,
    ) -> NotificationTemplate:
        from app.core.exceptions import NotFoundError
        template = await self.template_repo.get_by_tenant(template_id, tenant_id)
        if template is None:
            raise NotFoundError("Notification template not found.")
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(template, field, value)
        await self.template_repo.session.flush()
        await self.template_repo.session.refresh(template)
        return template

    async def delete_template(
        self, template_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        from app.core.exceptions import NotFoundError
        template = await self.template_repo.get_by_tenant(template_id, tenant_id)
        if template is None:
            raise NotFoundError("Notification template not found.")
        await self.template_repo.session.delete(template)
        await self.template_repo.session.flush()
