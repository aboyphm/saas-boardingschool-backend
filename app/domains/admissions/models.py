from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel, TimestampMixin
from app.shared.enums import AdmissionBatchStatus, AdmissionStatus


class AdmissionBatch(BaseModel, TimestampMixin):
    __tablename__ = "admission_batches"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    open_date: Mapped[date] = mapped_column(Date, nullable=False)
    close_date: Mapped[date] = mapped_column(Date, nullable=False)
    quota: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[AdmissionBatchStatus] = mapped_column(
        String(20), nullable=False, default=AdmissionBatchStatus.OPEN,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Admission(BaseModel, TimestampMixin):
    __tablename__ = "admissions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admission_batches.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    applicant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    origin_school: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[AdmissionStatus] = mapped_column(
        String(20), nullable=False, default=AdmissionStatus.SUBMITTED,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
