from __future__ import annotations
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column
from app.shared.base_model import BaseModel


class CorsOrigin(BaseModel):
    __tablename__ = "cors_origins"

    origin: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
