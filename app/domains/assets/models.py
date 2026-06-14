from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel, TimestampMixin
from app.shared.enums import AssetCategory, AssetCondition


class Asset(BaseModel, TimestampMixin):
    __tablename__ = "assets"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[AssetCategory] = mapped_column(
        String(30), nullable=False, default=AssetCategory.OTHER,
    )
    serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    condition: Mapped[AssetCondition] = mapped_column(
        String(20), nullable=False, default=AssetCondition.GOOD,
    )
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    purchase_price: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
