from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel, SoftDeleteMixin
from app.shared.enums import EmploymentType, Gender


class Teacher(BaseModel, SoftDeleteMixin):
    """Staff / teacher entity linked to a user account."""

    __tablename__ = "teachers"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nip", name="uq_teacher_nip_tenant"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ─── Identification ───────────────────────────────────────────────────────
    nip: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    gender: Mapped[Gender] = mapped_column(String(10), nullable=False)

    # ─── Professional ─────────────────────────────────────────────────────────
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    specialization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    qualification: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subjects: Mapped[list] = mapped_column(JSON, default=list)

    is_homeroom_teacher: Mapped[bool] = mapped_column(default=False, nullable=False)
    homeroom_class_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("class_rooms.id", ondelete="SET NULL"),
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    employment_type: Mapped[EmploymentType] = mapped_column(
        String(20), nullable=False, default=EmploymentType.FULL_TIME
    )
    join_date: Mapped[date | None] = mapped_column(Date, nullable=True)
