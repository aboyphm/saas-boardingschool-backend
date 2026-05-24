"""exams: exam_questions, exams, exam_question_map, exam_sessions, exam_answers

Revision ID: 010
Revises: 009
Create Date: 2026-05-24
"""
from __future__ import annotations
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "exam_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("grade_level", sa.String(10), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("question_type", sa.String(10), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("options", postgresql.JSONB(), nullable=True),
        sa.Column("correct_option", sa.Integer(), nullable=True),
        sa.Column("points", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_exam_questions_tenant_id", "exam_questions", ["tenant_id"])
    op.create_index("ix_exam_questions_subject_id", "exam_questions", ["subject_id"])
    op.create_index("ix_exam_questions_grade_level", "exam_questions", ["grade_level"])

    op.create_table(
        "exams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("class_room_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("class_rooms.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("academic_year_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("semester", sa.Integer(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(15), nullable=False, server_default="DRAFT"),
        sa.Column("passing_score", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("shuffle_questions", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("shuffle_options", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_exams_tenant_id", "exams", ["tenant_id"])
    op.create_index("ix_exams_class_room_id", "exams", ["class_room_id"])
    op.create_index("ix_exams_status", "exams", ["status"])

    op.create_table(
        "exam_question_map",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("exam_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("exam_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("exam_id", "question_id", name="uq_exam_question"),
    )
    op.create_index("ix_exam_question_map_exam_id", "exam_question_map", ["exam_id"])

    op.create_table(
        "exam_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exam_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shuffled_ids", postgresql.JSONB(), nullable=False),
        sa.Column("option_maps", postgresql.JSONB(), nullable=False),
        sa.Column("score_mcq", sa.Float(), nullable=True),
        sa.Column("score_essay", sa.Float(), nullable=True),
        sa.Column("total_score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(15), nullable=False, server_default="IN_PROGRESS"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("exam_id", "student_id", name="uq_exam_session"),
    )
    op.create_index("ix_exam_sessions_tenant_id", "exam_sessions", ["tenant_id"])
    op.create_index("ix_exam_sessions_exam_id", "exam_sessions", ["exam_id"])
    op.create_index("ix_exam_sessions_student_id", "exam_sessions", ["student_id"])

    op.create_table(
        "exam_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("exam_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("exam_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("selected_option", sa.Integer(), nullable=True),
        sa.Column("essay_text", sa.Text(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("points_earned", sa.Float(), nullable=True),
        sa.Column("graded_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("session_id", "question_id", name="uq_answer_session_question"),
    )
    op.create_index("ix_exam_answers_session_id", "exam_answers", ["session_id"])


def downgrade() -> None:
    op.drop_table("exam_answers")
    op.drop_table("exam_sessions")
    op.drop_table("exam_question_map")
    op.drop_table("exams")
    op.drop_table("exam_questions")
