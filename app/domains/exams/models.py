from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TIMESTAMP

from app.shared.base_model import BaseModel, TimestampMixin


class ExamQuestion(BaseModel, TimestampMixin):
    __tablename__ = "exam_questions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teachers.id", ondelete="SET NULL"),
        nullable=True,
    )
    grade_level: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    question_type: Mapped[str] = mapped_column(String(10), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    correct_option: Mapped[int | None] = mapped_column(Integer, nullable=True)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class Exam(BaseModel, TimestampMixin):
    __tablename__ = "exams"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="RESTRICT"),
        nullable=False,
    )
    class_room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("class_rooms.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_years.id", ondelete="RESTRICT"),
        nullable=False,
    )
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    scheduled_at: Mapped[str | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="DRAFT", index=True)
    passing_score: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    shuffle_questions: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    shuffle_options: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ExamQuestionMap(BaseModel, TimestampMixin):
    __tablename__ = "exam_question_map"
    __table_args__ = (
        UniqueConstraint("exam_id", "question_id", name="uq_exam_question"),
    )

    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exam_questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)


class ExamSession(BaseModel, TimestampMixin):
    __tablename__ = "exam_sessions"
    __table_args__ = (
        UniqueConstraint("exam_id", "student_id", name="uq_exam_session"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    started_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    submitted_at: Mapped[str | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    shuffled_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    option_maps: Mapped[dict] = mapped_column(JSONB, nullable=False)
    score_mcq: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_essay: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="IN_PROGRESS")


class ExamAnswer(BaseModel, TimestampMixin):
    __tablename__ = "exam_answers"
    __table_args__ = (
        UniqueConstraint("session_id", "question_id", name="uq_answer_session_question"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exam_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exam_questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    selected_option: Mapped[int | None] = mapped_column(Integer, nullable=True)
    essay_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    points_earned: Mapped[float | None] = mapped_column(Float, nullable=True)
    graded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teachers.id", ondelete="SET NULL"),
        nullable=True,
    )
    graded_at: Mapped[str | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
