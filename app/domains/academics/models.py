from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel, TimestampMixin
from app.shared.enums import Semester, SubjectType


class AcademicYear(BaseModel, TimestampMixin):
    """Defines a single academic year (e.g., 2024/2025) for a tenant."""

    __tablename__ = "academic_years"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_academic_year_name_tenant"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    semester_1_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    semester_1_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    semester_2_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    semester_2_end: Mapped[date | None] = mapped_column(Date, nullable=True)


class ClassRoom(BaseModel, TimestampMixin):
    """A class section within an academic year."""

    __tablename__ = "class_rooms"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_years.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    grade_level: Mapped[str] = mapped_column(String(20), nullable=False)
    homeroom_teacher_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teachers.id", ondelete="SET NULL"),
        nullable=True,
    )
    capacity: Mapped[int] = mapped_column(Integer, default=30)
    current_count: Mapped[int] = mapped_column(Integer, default=0)


class Subject(BaseModel, TimestampMixin):
    """A course or subject taught within a tenant."""

    __tablename__ = "subjects"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_subject_code_tenant"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    credit_hours: Mapped[int] = mapped_column(Integer, default=2)
    subject_type: Mapped[SubjectType] = mapped_column(
        String(30), nullable=False, default=SubjectType.GENERAL
    )


class Assignment(BaseModel, TimestampMixin):
    """An assignment or task issued by a teacher for a specific class."""

    __tablename__ = "assignments"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teachers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("class_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, default=100)


class Grade(BaseModel, TimestampMixin):
    """A student's grade for a subject in a given semester."""

    __tablename__ = "grades"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "student_id", "subject_id", "academic_year_id", "semester",
            name="uq_grade_student_subject_semester",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_years.id", ondelete="CASCADE"),
        nullable=False,
    )
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    grade_letter: Mapped[str | None] = mapped_column(String(5), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ClassEnrollment(BaseModel, TimestampMixin):
    __tablename__ = "class_enrollments"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "student_id", "academic_year_id",
            name="uq_enrollment_student_year",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    class_room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("class_rooms.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_years.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    enrolled_at: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class SchoolEvent(BaseModel, TimestampMixin):
    __tablename__ = "school_events"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class ScheduleSlot(BaseModel, TimestampMixin):
    __tablename__ = "schedule_slots"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "class_room_id", "academic_year_id", "day_of_week", "time_start",
            name="uq_slot_class_day_time",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    class_room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("class_rooms.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_years.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teachers.id", ondelete="SET NULL"),
        nullable=True,
    )
    day_of_week: Mapped[str] = mapped_column(String(10), nullable=False)
    time_start: Mapped[str] = mapped_column(String(5), nullable=False)
    time_end: Mapped[str] = mapped_column(String(5), nullable=False)
