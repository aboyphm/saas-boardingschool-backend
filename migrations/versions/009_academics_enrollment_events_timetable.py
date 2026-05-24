"""academics: class_enrollments, school_events, schedule_slots; extend academic_years

Revision ID: 009
Revises: 008
Create Date: 2026-05-22
"""
from __future__ import annotations
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extend academic_years with semester dates
    op.add_column("academic_years", sa.Column("semester_1_start", sa.Date(), nullable=True))
    op.add_column("academic_years", sa.Column("semester_1_end",   sa.Date(), nullable=True))
    op.add_column("academic_years", sa.Column("semester_2_start", sa.Date(), nullable=True))
    op.add_column("academic_years", sa.Column("semester_2_end",   sa.Date(), nullable=True))

    # class_enrollments
    op.create_table(
        "class_enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("class_room_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("class_rooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_year_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enrolled_at", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "student_id", "academic_year_id",
                            name="uq_enrollment_student_year"),
    )
    op.create_index("ix_class_enrollments_tenant_id", "class_enrollments", ["tenant_id"])
    op.create_index("ix_class_enrollments_student_id", "class_enrollments", ["student_id"])
    op.create_index("ix_class_enrollments_class_room_id", "class_enrollments", ["class_room_id"])
    op.create_index("ix_class_enrollments_academic_year_id", "class_enrollments", ["academic_year_id"])

    # school_events
    op.create_table(
        "school_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to",   sa.Date(), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_school_events_tenant_id", "school_events", ["tenant_id"])

    # schedule_slots
    op.create_table(
        "schedule_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("class_room_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("class_rooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_year_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("day_of_week", sa.String(10), nullable=False),
        sa.Column("time_start",  sa.String(5), nullable=False),
        sa.Column("time_end",    sa.String(5), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "class_room_id", "academic_year_id",
                            "day_of_week", "time_start", name="uq_slot_class_day_time"),
    )
    op.create_index("ix_schedule_slots_tenant_id", "schedule_slots", ["tenant_id"])
    op.create_index("ix_schedule_slots_class_room_id", "schedule_slots", ["class_room_id"])
    op.create_index("ix_schedule_slots_academic_year_id", "schedule_slots", ["academic_year_id"])


def downgrade() -> None:
    op.drop_table("schedule_slots")
    op.drop_table("school_events")
    op.drop_table("class_enrollments")
    op.drop_column("academic_years", "semester_2_end")
    op.drop_column("academic_years", "semester_2_start")
    op.drop_column("academic_years", "semester_1_end")
    op.drop_column("academic_years", "semester_1_start")
