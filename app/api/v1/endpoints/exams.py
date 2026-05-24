from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_active_user, require_roles
from app.core.database import AsyncSession, get_db
from app.core.exceptions import ForbiddenError
from app.domains.exams.repository import (
    ExamAnswerRepository,
    ExamQuestionMapRepository,
    ExamQuestionRepository,
    ExamRepository,
    ExamSessionRepository,
)
from app.domains.exams.schemas import (
    AddQuestionToExamRequest,
    AnswerRequest,
    ExamCreate,
    ExamQuestionMapResponse,
    ExamResponse,
    ExamUpdate,
    GradeEssaysRequest,
    QuestionCreate,
    QuestionResponse,
    QuestionUpdate,
    ResultsResponse,
    SessionResponse,
)
from app.domains.exams.service import ExamsService
from app.domains.users.models import User
from app.shared.enums import UserRole

router = APIRouter()


def _tid(user: User) -> uuid.UUID:
    if user.tenant_id is None:
        raise ForbiddenError("A tenant context is required.")
    return user.tenant_id


def _get_service(db: AsyncSession) -> ExamsService:
    return ExamsService(
        question_repo=ExamQuestionRepository(db),
        exam_repo=ExamRepository(db),
        map_repo=ExamQuestionMapRepository(db),
        session_repo=ExamSessionRepository(db),
        answer_repo=ExamAnswerRepository(db),
    )


# ── Question Bank ──────────────────────────────────────────────────────────────

@router.get("/questions", response_model=list[QuestionResponse])
async def list_questions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    subject_id: uuid.UUID | None = Query(default=None),
    grade_level: str | None = Query(default=None),
    category: str | None = Query(default=None),
    question_type: str | None = Query(default=None),
) -> list[QuestionResponse]:
    svc = _get_service(db)
    questions = await svc.list_questions(_tid(current_user), subject_id, grade_level, category, question_type)
    return [QuestionResponse.model_validate(q) for q in questions]


@router.post("/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(
    data: QuestionCreate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TEACHER, UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QuestionResponse:
    svc = _get_service(db)
    q = await svc.create_question(data, _tid(current_user), teacher_id=current_user.id)
    return QuestionResponse.model_validate(q)


@router.put("/questions/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: uuid.UUID,
    data: QuestionUpdate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TEACHER, UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QuestionResponse:
    svc = _get_service(db)
    q = await svc.update_question(question_id, data, _tid(current_user))
    return QuestionResponse.model_validate(q)


@router.delete("/questions/{question_id}", status_code=status.HTTP_200_OK)
async def delete_question(
    question_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TEACHER, UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    svc = _get_service(db)
    await svc.delete_question(question_id, _tid(current_user))
    return {"ok": True}


# ── Exam Management ────────────────────────────────────────────────────────────

@router.get("", response_model=list[ExamResponse])
async def list_exams(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    class_id: uuid.UUID | None = Query(default=None),
    academic_year_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
) -> list[ExamResponse]:
    svc = _get_service(db)
    exams = await svc.list_exams(_tid(current_user), class_id, academic_year_id, status)
    return [ExamResponse.model_validate(e) for e in exams]


@router.post("", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
async def create_exam(
    data: ExamCreate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TEACHER, UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExamResponse:
    svc = _get_service(db)
    exam = await svc.create_exam(data, _tid(current_user))
    return ExamResponse.model_validate(exam)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionResponse:
    svc = _get_service(db)
    session, questions = await svc.get_session(session_id, _tid(current_user))
    resp = SessionResponse.model_validate(session)
    safe_questions = []
    for q in questions:
        qr = QuestionResponse.model_validate(q)
        qr.correct_option = None
        safe_questions.append(qr)
    resp.questions = safe_questions
    return resp


@router.post("/sessions/{session_id}/answer")
async def save_answer(
    session_id: uuid.UUID,
    data: AnswerRequest,
    current_user: Annotated[User, Depends(require_roles(UserRole.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    svc = _get_service(db)
    await svc.save_answer(session_id, data, _tid(current_user))
    return {"ok": True}


@router.post("/sessions/{session_id}/submit", response_model=SessionResponse)
async def submit_session(
    session_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(UserRole.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionResponse:
    svc = _get_service(db)
    session = await svc.submit_session(session_id, _tid(current_user))
    return SessionResponse.model_validate(session)


@router.get("/sessions/{session_id}/result", response_model=SessionResponse)
async def get_session_result(
    session_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionResponse:
    svc = _get_service(db)
    session = await svc.get_session_result(session_id, _tid(current_user))
    return SessionResponse.model_validate(session)


@router.post("/sessions/{session_id}/grade", response_model=SessionResponse)
async def grade_essays(
    session_id: uuid.UUID,
    data: GradeEssaysRequest,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TEACHER, UserRole.TENANT_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionResponse:
    svc = _get_service(db)
    session = await svc.grade_essays(session_id, data, current_user.id, _tid(current_user))
    return SessionResponse.model_validate(session)


@router.get("/{exam_id}", response_model=ExamResponse)
async def get_exam(
    exam_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExamResponse:
    svc = _get_service(db)
    exam = await svc.get_exam_or_404(exam_id, _tid(current_user))
    return ExamResponse.model_validate(exam)


@router.put("/{exam_id}", response_model=ExamResponse)
async def update_exam(
    exam_id: uuid.UUID,
    data: ExamUpdate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TEACHER, UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExamResponse:
    svc = _get_service(db)
    exam = await svc.update_exam(exam_id, data, _tid(current_user))
    return ExamResponse.model_validate(exam)


@router.delete("/{exam_id}", status_code=status.HTTP_200_OK)
async def delete_exam(
    exam_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TEACHER, UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    svc = _get_service(db)
    await svc.delete_exam(exam_id, _tid(current_user))
    return {"ok": True}


@router.post("/{exam_id}/publish", response_model=ExamResponse)
async def publish_exam(
    exam_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TEACHER, UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExamResponse:
    svc = _get_service(db)
    exam = await svc.publish_exam(exam_id, _tid(current_user))
    return ExamResponse.model_validate(exam)


@router.post("/{exam_id}/activate", response_model=ExamResponse)
async def activate_exam(
    exam_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExamResponse:
    svc = _get_service(db)
    exam = await svc.activate_exam(exam_id, _tid(current_user))
    return ExamResponse.model_validate(exam)


@router.post("/{exam_id}/complete", response_model=ExamResponse)
async def complete_exam(
    exam_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExamResponse:
    svc = _get_service(db)
    exam = await svc.complete_exam(exam_id, _tid(current_user))
    return ExamResponse.model_validate(exam)


@router.get("/{exam_id}/questions", response_model=list[QuestionResponse])
async def list_exam_questions(
    exam_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[QuestionResponse]:
    svc = _get_service(db)
    questions = await svc.list_exam_questions(exam_id, _tid(current_user))
    return [QuestionResponse.model_validate(q) for q in questions]


@router.post("/{exam_id}/questions", response_model=ExamQuestionMapResponse, status_code=status.HTTP_201_CREATED)
async def add_question_to_exam(
    exam_id: uuid.UUID,
    data: AddQuestionToExamRequest,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TEACHER, UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExamQuestionMapResponse:
    svc = _get_service(db)
    mapping = await svc.add_question_to_exam(exam_id, data.question_id, _tid(current_user))
    return ExamQuestionMapResponse.model_validate(mapping)


@router.delete("/{exam_id}/questions/{question_id}", status_code=status.HTTP_200_OK)
async def remove_question_from_exam(
    exam_id: uuid.UUID,
    question_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TEACHER, UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    svc = _get_service(db)
    await svc.remove_question_from_exam(exam_id, question_id, _tid(current_user))
    return {"ok": True}


@router.post("/{exam_id}/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    exam_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(UserRole.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionResponse:
    svc = _get_service(db)
    session = await svc.start_session(exam_id, current_user.id, _tid(current_user))
    return SessionResponse.model_validate(session)


@router.get("/{exam_id}/grade")
async def list_ungraded_sessions(
    exam_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TEACHER, UserRole.TENANT_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list:
    svc = _get_service(db)
    return await svc.list_ungraded_sessions(exam_id, _tid(current_user))


@router.get("/{exam_id}/results", response_model=ResultsResponse)
async def get_results(
    exam_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TEACHER, UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResultsResponse:
    svc = _get_service(db)
    return await svc.get_results(exam_id, _tid(current_user))
