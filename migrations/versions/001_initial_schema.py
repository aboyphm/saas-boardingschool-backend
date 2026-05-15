"""Initial schema — all domain tables

Revision ID: 001
Revises:
Create Date: 2025-05-10 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── Extensions ───────────────────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # ─── tenants ──────────────────────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("subdomain", sa.String(100), nullable=False, unique=True),
        sa.Column("custom_domain", sa.String(255), nullable=True, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="trial"),
        sa.Column("plan", sa.String(20), nullable=False, server_default="free"),
        sa.Column("logo_url", sa.Text, nullable=True),
        sa.Column("favicon_url", sa.Text, nullable=True),
        sa.Column("primary_color", sa.String(10), server_default="#1E40AF"),
        sa.Column("secondary_color", sa.String(10), server_default="#64748B"),
        sa.Column("font_family", sa.String(100), server_default="Inter"),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(30), nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), server_default="Indonesia"),
        sa.Column("timezone", sa.String(60), server_default="Asia/Jakarta"),
        sa.Column("max_students", sa.Integer, server_default="500"),
        sa.Column("max_teachers", sa.Integer, server_default="50"),
        sa.Column("max_storage_gb", sa.Integer, server_default="10"),
        sa.Column("storage_used_gb", sa.Float, server_default="0.0"),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subscription_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settings", postgresql.JSON, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])
    op.create_index("ix_tenants_subdomain", "tenants", ["subdomain"])
    op.create_index("ix_tenants_status", "tenants", ["status"])

    # ─── tenant_brandings ─────────────────────────────────────────────────────
    op.create_table(
        "tenant_brandings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("login_page_config", postgresql.JSON, server_default="{}"),
        sa.Column("dashboard_layout", postgresql.JSON, server_default="{}"),
        sa.Column("email_template", postgresql.JSON, server_default="{}"),
        sa.Column("pdf_header_html", sa.Text, nullable=True),
        sa.Column("pdf_footer_html", sa.Text, nullable=True),
        sa.Column("whatsapp_sender_name", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ─── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(100), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("avatar_url", sa.Text, nullable=True),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("is_verified", sa.Boolean, server_default="false"),
        sa.Column("is_deleted", sa.Boolean, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("mfa_enabled", sa.Boolean, server_default="false"),
        sa.Column("mfa_secret", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("email", "tenant_id", name="uq_user_email_tenant"),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_is_deleted", "users", ["is_deleted"])

    # ─── role_permissions ─────────────────────────────────────────────────────
    op.create_table(
        "role_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("permissions", postgresql.JSON, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),
    )

    # ─── user_sessions ────────────────────────────────────────────────────────
    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_token_hash", sa.String(255), nullable=False),
        sa.Column("device_info", postgresql.JSON, server_default="{}"),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_revoked", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_refresh_token_hash", "user_sessions", ["refresh_token_hash"])

    # ─── password_reset_tokens ────────────────────────────────────────────────
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_used", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ─── academic_years ───────────────────────────────────────────────────────
    op.create_table(
        "academic_years",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(20), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "name", name="uq_academic_year_name_tenant"),
    )

    # ─── class_rooms ──────────────────────────────────────────────────────────
    op.create_table(
        "class_rooms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_year_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("grade_level", sa.String(20), nullable=False),
        sa.Column("homeroom_teacher_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("capacity", sa.Integer, server_default="30"),
        sa.Column("current_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ─── subjects ─────────────────────────────────────────────────────────────
    op.create_table(
        "subjects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("credit_hours", sa.Integer, server_default="2"),
        sa.Column("subject_type", sa.String(30), server_default="general"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "code", name="uq_subject_code_tenant"),
    )

    # ─── students ─────────────────────────────────────────────────────────────
    op.create_table(
        "students",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("nis", sa.String(30), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("gender", sa.String(10), nullable=False),
        sa.Column("birth_date", sa.Date, nullable=True),
        sa.Column("birth_place", sa.String(100), nullable=True),
        sa.Column("religion", sa.String(50), server_default="Islam"),
        sa.Column("nationality", sa.String(50), server_default="Indonesian"),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("emergency_contact_name", sa.String(255), nullable=True),
        sa.Column("emergency_contact_phone", sa.String(30), nullable=True),
        sa.Column("photo_url", sa.Text, nullable=True),
        sa.Column("blood_type", sa.String(5), nullable=True),
        sa.Column("health_notes", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("enrollment_date", sa.Date, nullable=True),
        sa.Column("graduation_date", sa.Date, nullable=True),
        sa.Column("academic_year", sa.String(20), nullable=True),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("class_rooms.id", ondelete="SET NULL"), nullable=True),
        sa.Column("dormitory_room_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "nis", name="uq_student_nis_tenant"),
    )
    op.create_index("ix_students_tenant_id", "students", ["tenant_id"])
    op.create_index("ix_students_status", "students", ["status"])

    # ─── student_parents ──────────────────────────────────────────────────────
    op.create_table(
        "student_parents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_type", sa.String(20), nullable=False),
        sa.Column("is_primary", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("student_id", "parent_user_id", name="uq_student_parent"),
    )

    # ─── teachers ─────────────────────────────────────────────────────────────
    op.create_table(
        "teachers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("nip", sa.String(30), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("gender", sa.String(10), nullable=False),
        sa.Column("birth_date", sa.Date, nullable=True),
        sa.Column("specialization", sa.String(255), nullable=True),
        sa.Column("qualification", sa.String(255), nullable=True),
        sa.Column("subjects", postgresql.JSON, server_default="[]"),
        sa.Column("is_homeroom_teacher", sa.Boolean, server_default="false"),
        sa.Column("homeroom_class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("class_rooms.id", ondelete="SET NULL"), nullable=True),
        sa.Column("employment_type", sa.String(20), server_default="full_time"),
        sa.Column("join_date", sa.Date, nullable=True),
        sa.Column("is_deleted", sa.Boolean, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "nip", name="uq_teacher_nip_tenant"),
    )

    # ─── assignments ──────────────────────────────────────────────────────────
    op.create_table(
        "assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("class_rooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("max_score", sa.Integer, server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ─── grades ───────────────────────────────────────────────────────────────
    op.create_table(
        "grades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_year_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False),
        sa.Column("semester", sa.Integer, nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("grade_letter", sa.String(5), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "student_id", "subject_id", "academic_year_id", "semester", name="uq_grade_student_subject_semester"),
    )

    # ─── attendance_records ───────────────────────────────────────────────────
    op.create_table(
        "attendance_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("class_rooms.id", ondelete="SET NULL"), nullable=True),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("check_in_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_out_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("recorded_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("input_method", sa.String(20), server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_attendance_records_tenant_date", "attendance_records", ["tenant_id", "date"])

    # ─── leave_requests ───────────────────────────────────────────────────────
    op.create_table(
        "leave_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_date", sa.Date, nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ─── dormitory_buildings ──────────────────────────────────────────────────
    op.create_table(
        "dormitory_buildings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("gender_type", sa.String(10), nullable=False),
        sa.Column("capacity", sa.Integer, nullable=False),
        sa.Column("location_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ─── dormitory_rooms ──────────────────────────────────────────────────────
    op.create_table(
        "dormitory_rooms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("building_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dormitory_buildings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("room_number", sa.String(20), nullable=False),
        sa.Column("floor", sa.Integer, nullable=True),
        sa.Column("capacity", sa.Integer, nullable=False),
        sa.Column("current_occupancy", sa.Integer, server_default="0"),
        sa.Column("status", sa.String(20), server_default="available"),
        sa.Column("room_type", sa.String(20), server_default="standard"),
        sa.Column("facilities", postgresql.JSON, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ─── dormitory_assignments ────────────────────────────────────────────────
    op.create_table(
        "dormitory_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dormitory_rooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bed_number", sa.String(10), nullable=True),
        sa.Column("assigned_date", sa.Date, nullable=False),
        sa.Column("vacated_date", sa.Date, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ─── dormitory_supervisors ────────────────────────────────────────────────
    op.create_table(
        "dormitory_supervisors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("building_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dormitory_buildings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_date", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ─── fee_categories ───────────────────────────────────────────────────────
    op.create_table(
        "fee_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("is_recurring", sa.Boolean, server_default="false"),
        sa.Column("billing_cycle", sa.String(20), server_default="monthly"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ─── invoices ─────────────────────────────────────────────────────────────
    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_number", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("subtotal", sa.Numeric(15, 2), nullable=False),
        sa.Column("discount", sa.Numeric(15, 2), server_default="0"),
        sa.Column("tax_rate", sa.Numeric(5, 2), server_default="0"),
        sa.Column("tax_amount", sa.Numeric(15, 2), server_default="0"),
        sa.Column("total_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("payment_gateway", sa.String(50), nullable=True),
        sa.Column("payment_reference", sa.String(255), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("items", postgresql.JSON, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "invoice_number", name="uq_invoice_number_tenant"),
    )
    op.create_index("ix_invoices_tenant_id", "invoices", ["tenant_id"])
    op.create_index("ix_invoices_status", "invoices", ["status"])
    op.create_index("ix_invoices_due_date", "invoices", ["due_date"])

    # ─── payments ─────────────────────────────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("payment_method", sa.String(50), nullable=False),
        sa.Column("payment_reference", sa.String(255), nullable=True),
        sa.Column("gateway_response", postgresql.JSON, server_default="{}"),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ─── payroll_records ──────────────────────────────────────────────────────
    op.create_table(
        "payroll_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_month", sa.Integer, nullable=False),
        sa.Column("period_year", sa.Integer, nullable=False),
        sa.Column("base_salary", sa.Numeric(15, 2), nullable=False),
        sa.Column("allowances", postgresql.JSON, server_default="{}"),
        sa.Column("deductions", postgresql.JSON, server_default="{}"),
        sa.Column("net_salary", sa.Numeric(15, 2), nullable=False),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "teacher_id", "period_month", "period_year", name="uq_payroll_teacher_period"),
    )

    # ─── notification_templates ───────────────────────────────────────────────
    op.create_table(
        "notification_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("body_template", sa.Text, nullable=False),
        sa.Column("variables", postgresql.JSON, server_default="[]"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ─── notification_logs ────────────────────────────────────────────────────
    op.create_table(
        "notification_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("retry_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notification_logs_tenant_id", "notification_logs", ["tenant_id"])
    op.create_index("ix_notification_logs_status", "notification_logs", ["status"])


def downgrade() -> None:
    op.drop_table("notification_logs")
    op.drop_table("notification_templates")
    op.drop_table("payroll_records")
    op.drop_table("payments")
    op.drop_table("invoices")
    op.drop_table("fee_categories")
    op.drop_table("dormitory_supervisors")
    op.drop_table("dormitory_assignments")
    op.drop_table("dormitory_rooms")
    op.drop_table("dormitory_buildings")
    op.drop_table("leave_requests")
    op.drop_table("attendance_records")
    op.drop_table("grades")
    op.drop_table("assignments")
    op.drop_table("student_parents")
    op.drop_table("students")
    op.drop_table("teachers")
    op.drop_table("subjects")
    op.drop_table("class_rooms")
    op.drop_table("academic_years")
    op.drop_table("password_reset_tokens")
    op.drop_table("user_sessions")
    op.drop_table("role_permissions")
    op.drop_table("users")
    op.drop_table("tenant_brandings")
    op.drop_table("tenants")
