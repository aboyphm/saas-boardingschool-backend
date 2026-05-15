from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel, SoftDeleteMixin, TimestampMixin
from app.shared.enums import Gender, ParentRelationship, StudentStatus


class Student(BaseModel, SoftDeleteMixin):
    """
    Core student entity.

    A student record is always scoped to a tenant. The ``user_id`` link is
    optional — a student may exist without a portal account until one is
    provisioned.
    """

    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nis", name="uq_student_nis_tenant"),
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
    nis: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    gender: Mapped[Gender] = mapped_column(String(10), nullable=False)

    # ─── Personal ─────────────────────────────────────────────────────────────
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    birth_place: Mapped[str | None] = mapped_column(String(100), nullable=True)
    religion: Mapped[str] = mapped_column(String(50), default="Islam")
    nationality: Mapped[str] = mapped_column(String(50), default="Indonesian")
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # ─── Emergency contact ────────────────────────────────────────────────────
    emergency_contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # ─── Health ───────────────────────────────────────────────────────────────
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    blood_type: Mapped[str | None] = mapped_column(String(5), nullable=True)
    health_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── Academic ─────────────────────────────────────────────────────────────
    status: Mapped[StudentStatus] = mapped_column(
        String(20), nullable=False, default=StudentStatus.ACTIVE, index=True
    )
    enrollment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    graduation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    academic_year: Mapped[str | None] = mapped_column(String(20), nullable=True)

    class_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("class_rooms.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dormitory_room_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dormitory_rooms.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ─── Relationships ────────────────────────────────────────────────────────
    parents: Mapped[list["StudentParent"]] = relationship(
        "StudentParent", back_populates="student", cascade="all, delete-orphan"
    )


class StudentParent(BaseModel, TimestampMixin):
    """Many-to-many link between students and their parent/guardian accounts."""

    __tablename__ = "student_parents"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "parent_user_id", name="uq_student_parent"
        ),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[ParentRelationship] = mapped_column(
        String(20), nullable=False
    )
    is_primary: Mapped[bool] = mapped_column(default=False, nullable=False)

    # ─── Relationships ────────────────────────────────────────────────────────
    student: Mapped["Student"] = relationship("Student", back_populates="parents")
