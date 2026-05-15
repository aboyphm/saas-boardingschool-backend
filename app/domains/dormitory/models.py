from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel, TimestampMixin
from app.shared.enums import DormitoryRoomStatus, DormitoryRoomType, Gender


class DormitoryBuilding(BaseModel, TimestampMixin):
    """A physical building in the dormitory complex."""

    __tablename__ = "dormitory_buildings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    gender_type: Mapped[Gender] = mapped_column(String(10), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    location_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class DormitoryRoom(BaseModel, TimestampMixin):
    """A single room within a dormitory building."""

    __tablename__ = "dormitory_rooms"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    building_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dormitory_buildings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    room_number: Mapped[str] = mapped_column(String(20), nullable=False)
    floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    current_occupancy: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[DormitoryRoomStatus] = mapped_column(
        String(20), nullable=False, default=DormitoryRoomStatus.AVAILABLE, index=True
    )
    room_type: Mapped[DormitoryRoomType] = mapped_column(
        String(20), nullable=False, default=DormitoryRoomType.STANDARD
    )
    facilities: Mapped[list] = mapped_column(JSON, default=list)


class DormitoryAssignment(BaseModel, TimestampMixin):
    """Records which student occupies which bed/room."""

    __tablename__ = "dormitory_assignments"

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
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dormitory_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bed_number: Mapped[str | None] = mapped_column(String(10), nullable=True)
    assigned_date: Mapped[date] = mapped_column(Date, nullable=False)
    vacated_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)


class DormitorySupervisor(BaseModel, TimestampMixin):
    """Assigns a teacher/supervisor to a dormitory building."""

    __tablename__ = "dormitory_supervisors"

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
    )
    building_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dormitory_buildings.id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_date: Mapped[date] = mapped_column(Date, nullable=False)
