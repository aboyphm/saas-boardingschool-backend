from __future__ import annotations

import uuid
from datetime import datetime

from app.shared.base_schema import BaseSchema
from app.shared.enums import NotificationChannel, NotificationStatus


class NotificationTemplateCreate(BaseSchema):
    tenant_id: uuid.UUID | None = None
    name: str
    channel: NotificationChannel
    subject: str | None = None
    body_template: str
    variables: list[str] = []


class NotificationTemplateResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    channel: NotificationChannel
    subject: str | None
    body_template: str
    variables: list
    is_active: bool
    created_at: datetime


class SendNotificationRequest(BaseSchema):
    tenant_id: uuid.UUID
    recipient_user_id: uuid.UUID | None = None
    channel: NotificationChannel
    subject: str | None = None
    body: str
    template_id: uuid.UUID | None = None
    template_variables: dict = {}


class NotificationLogResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    recipient_user_id: uuid.UUID | None
    channel: NotificationChannel
    subject: str | None
    body: str
    status: NotificationStatus
    sent_at: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None
    error_message: str | None
    retry_count: int
    created_at: datetime
