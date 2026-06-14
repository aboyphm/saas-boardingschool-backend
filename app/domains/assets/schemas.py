from __future__ import annotations

import uuid
from datetime import date, datetime

from app.shared.base_schema import BaseSchema
from app.shared.enums import AssetCategory, AssetCondition


class AssetCreate(BaseSchema):
    name: str
    category: AssetCategory = AssetCategory.OTHER
    serial_number: str | None = None
    location: str | None = None
    condition: AssetCondition = AssetCondition.GOOD
    purchase_date: date | None = None
    purchase_price: float | None = None
    notes: str | None = None
    is_active: bool = True


class AssetUpdate(BaseSchema):
    name: str | None = None
    category: AssetCategory | None = None
    serial_number: str | None = None
    location: str | None = None
    condition: AssetCondition | None = None
    purchase_date: date | None = None
    purchase_price: float | None = None
    notes: str | None = None
    is_active: bool | None = None


class AssetResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    category: AssetCategory
    serial_number: str | None
    location: str | None
    condition: AssetCondition
    purchase_date: date | None
    purchase_price: float | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AssetStatsResponse(BaseSchema):
    total: int
    good: int
    fair: int
    poor: int
    broken: int
    lost: int
