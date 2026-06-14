from __future__ import annotations

import uuid
from datetime import datetime

from app.shared.base_schema import BaseSchema
from app.shared.enums import SubscriptionPlan


class SubscriptionPackageCreate(BaseSchema):
    plan: SubscriptionPlan
    name: str
    description: str | None = None
    price_monthly: float = 0.0
    price_yearly: float = 0.0
    feature_flags: list[str] = []
    quota_students: int = 0
    quota_teachers: int = 0
    quota_storage_gb: int = 0
    is_active: bool = True


class SubscriptionPackageUpdate(BaseSchema):
    name: str | None = None
    description: str | None = None
    price_monthly: float | None = None
    price_yearly: float | None = None
    feature_flags: list[str] | None = None
    quota_students: int | None = None
    quota_teachers: int | None = None
    quota_storage_gb: int | None = None
    is_active: bool | None = None


class SubscriptionPackageResponse(BaseSchema):
    id: uuid.UUID
    plan: str
    name: str
    description: str | None
    price_monthly: float
    price_yearly: float
    feature_flags: list[str]
    quota_students: int
    quota_teachers: int
    quota_storage_gb: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
