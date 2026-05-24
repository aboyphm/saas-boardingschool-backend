from __future__ import annotations

import uuid
import datetime as dt
from typing import Any

from app.shared.base_schema import BaseSchema
from app.shared.enums import QuestionType, ExamStatus, SessionStatus


# ── Question Bank ──────────────────────────────────────────────────────────────

class QuestionCreate(BaseSchema):
    subject_id: uuid.UUID
    grade_level: str
    category: str | None = None
    question_type: QuestionType
    body: str
    options: list[dict[str, str]] | None = None
    correct_option: int | None = None
    points: int = 1


class QuestionUpdate(BaseSchema):
    grade_level: str | None = None
    category: str | None = None
    body: str | None = None
    options: list[dict[str, str]] | None = None
    correct_option: int | None = None
    points: int | None = None


class QuestionResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    subject_id: uuid.UUID
    created_by: uuid.UUID | None
    grade_level: str
    category: str | None
    question_type: QuestionType
    body: str
    options: list[dict[str, Any]] | None
    correct_option: int | None
    points: int
    created_at: dt.datetime
    updated_at: dt.datetime


# ── Exam ───────────────────────────────────────────────────────────────────────

class ExamCreate(BaseSchema):
    title: str
    subject_id: uuid.UUID
    class_room_id: uuid.UUID
    academic_year_id: uuid.UUID
    semester: int
    duration_minutes: int
    scheduled_at: dt.datetime | None = None
    passing_score: int = 60
    shuffle_questions: bool = True
    shuffle_options: bool = True


class ExamUpdate(BaseSchema):
    title: str | None = None
    duration_minutes: int | None = None
    scheduled_at: dt.datetime | None = None
    passing_score: int | None = None
    shuffle_questions: bool | None = None
    shuffle_options: bool | None = None


class ExamResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    subject_id: uuid.UUID
    class_room_id: uuid.UUID
    academic_year_id: uuid.UUID
    semester: int
    duration_minutes: int
    scheduled_at: dt.datetime | None
    status: ExamStatus
    passing_score: int
    shuffle_questions: bool
    shuffle_options: bool
    created_at: dt.datetime
    updated_at: dt.datetime


class ExamQuestionMapResponse(BaseSchema):
    id: uuid.UUID
    exam_id: uuid.UUID
    question_id: uuid.UUID
    display_order: int


class AddQuestionToExamRequest(BaseSchema):
    question_id: uuid.UUID


class ReorderRequest(BaseSchema):
    items: list[dict[str, Any]]


# ── Session ────────────────────────────────────────────────────────────────────

class SessionResponse(BaseSchema):
    id: uuid.UUID
    exam_id: uuid.UUID
    student_id: uuid.UUID
    started_at: dt.datetime
    submitted_at: dt.datetime | None
    shuffled_ids: list[str]
    option_maps: dict[str, list[int]]
    score_mcq: float | None
    score_essay: float | None
    total_score: float | None
    status: SessionStatus
    questions: list[QuestionResponse] | None = None


class AnswerRequest(BaseSchema):
    question_id: uuid.UUID
    selected_option: int | None = None
    essay_text: str | None = None


# ── Essay Grading ──────────────────────────────────────────────────────────────

class GradeItem(BaseSchema):
    question_id: uuid.UUID
    points_earned: float


class GradeEssaysRequest(BaseSchema):
    grades: list[GradeItem]


# ── Results & Analytics ────────────────────────────────────────────────────────

class ResultSummary(BaseSchema):
    mean: float
    median: float
    highest: float
    lowest: float
    pass_rate: float
    total_students: int


class ResultsResponse(BaseSchema):
    summary: ResultSummary
    distribution: dict[str, int]
    per_question: list[dict[str, Any]]
    students: list[dict[str, Any]]
