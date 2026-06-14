from __future__ import annotations
import uuid
from datetime import datetime
from app.shared.base_schema import BaseSchema


class CorsOriginCreate(BaseSchema):
    origin: str
    description: str | None = None
    is_active: bool = True


class CorsOriginResponse(BaseSchema):
    id: uuid.UUID
    origin: str
    description: str | None
    is_active: bool
    created_at: datetime
