from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class SubscriptionPackage(BaseModel):
    __tablename__ = "subscription_packages"

    plan: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    price_monthly: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    price_yearly: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    feature_flags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    quota_students: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quota_teachers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quota_storage_gb: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
