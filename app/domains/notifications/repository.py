from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.notifications.models import NotificationLog, NotificationTemplate
from app.shared.base_repository import BaseRepository
from app.shared.enums import NotificationStatus


class NotificationTemplateRepository(BaseRepository[NotificationTemplate, dict, dict]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(NotificationTemplate, session)

    async def list_by_tenant(
        self, tenant_id: uuid.UUID
    ) -> list[NotificationTemplate]:
        stmt = (
            select(NotificationTemplate)
            .where(
                (NotificationTemplate.tenant_id == tenant_id)
                | NotificationTemplate.tenant_id.is_(None)
            )
            .order_by(NotificationTemplate.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_tenant(
        self, template_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> NotificationTemplate | None:
        stmt = select(NotificationTemplate).where(
            NotificationTemplate.id == template_id,
            NotificationTemplate.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class NotificationLogRepository(BaseRepository[NotificationLog, dict, dict]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(NotificationLog, session)

    async def list_pending(self, limit: int = 100) -> list[NotificationLog]:
        stmt = (
            select(NotificationLog)
            .where(
                NotificationLog.status == NotificationStatus.PENDING,
                NotificationLog.retry_count < 3,
            )
            .order_by(NotificationLog.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_user(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> list[NotificationLog]:
        stmt = (
            select(NotificationLog)
            .where(
                NotificationLog.recipient_user_id == user_id,
                NotificationLog.tenant_id == tenant_id,
            )
            .order_by(NotificationLog.created_at.desc())
            .limit(50)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
