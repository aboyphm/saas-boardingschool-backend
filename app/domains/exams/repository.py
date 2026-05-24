from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.exams.models import (
    Exam, ExamAnswer, ExamQuestion, ExamQuestionMap, ExamSession,
)
from app.domains.exams.schemas import (
    ExamCreate, ExamUpdate,
    QuestionCreate, QuestionUpdate,
)
from app.shared.base_repository import BaseRepository


class ExamQuestionRepository(BaseRepository[ExamQuestion, QuestionCreate, QuestionUpdate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ExamQuestion, session)

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        subject_id: uuid.UUID | None = None,
        grade_level: str | None = None,
        category: str | None = None,
        question_type: str | None = None,
    ) -> list[ExamQuestion]:
        stmt = select(ExamQuestion).where(ExamQuestion.tenant_id == tenant_id)
        if subject_id:
            stmt = stmt.where(ExamQuestion.subject_id == subject_id)
        if grade_level:
            stmt = stmt.where(ExamQuestion.grade_level == grade_level)
        if category:
            stmt = stmt.where(ExamQuestion.category == category)
        if question_type:
            stmt = stmt.where(ExamQuestion.question_type == question_type)
        stmt = stmt.order_by(ExamQuestion.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ExamRepository(BaseRepository[Exam, ExamCreate, ExamUpdate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Exam, session)

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        class_id: uuid.UUID | None = None,
        academic_year_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> list[Exam]:
        stmt = select(Exam).where(Exam.tenant_id == tenant_id)
        if class_id:
            stmt = stmt.where(Exam.class_room_id == class_id)
        if academic_year_id:
            stmt = stmt.where(Exam.academic_year_id == academic_year_id)
        if status:
            stmt = stmt.where(Exam.status == status)
        stmt = stmt.order_by(Exam.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ExamQuestionMapRepository(BaseRepository[ExamQuestionMap, ExamQuestionMap, ExamQuestionMap]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ExamQuestionMap, session)

    async def list_by_exam(self, exam_id: uuid.UUID) -> list[ExamQuestionMap]:
        stmt = (
            select(ExamQuestionMap)
            .where(ExamQuestionMap.exam_id == exam_id)
            .order_by(ExamQuestionMap.display_order)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_exam_question(
        self, exam_id: uuid.UUID, question_id: uuid.UUID
    ) -> ExamQuestionMap | None:
        stmt = select(ExamQuestionMap).where(
            ExamQuestionMap.exam_id == exam_id,
            ExamQuestionMap.question_id == question_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class ExamSessionRepository(BaseRepository[ExamSession, ExamSession, ExamSession]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ExamSession, session)

    async def get_by_exam_student(
        self, exam_id: uuid.UUID, student_id: uuid.UUID
    ) -> ExamSession | None:
        stmt = select(ExamSession).where(
            ExamSession.exam_id == exam_id,
            ExamSession.student_id == student_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_exam(self, exam_id: uuid.UUID) -> list[ExamSession]:
        stmt = select(ExamSession).where(ExamSession.exam_id == exam_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_submitted_by_exam(self, exam_id: uuid.UUID) -> list[ExamSession]:
        stmt = select(ExamSession).where(
            ExamSession.exam_id == exam_id,
            ExamSession.status == "SUBMITTED",
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ExamAnswerRepository(BaseRepository[ExamAnswer, ExamAnswer, ExamAnswer]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ExamAnswer, session)

    async def list_by_session(self, session_id: uuid.UUID) -> list[ExamAnswer]:
        stmt = select(ExamAnswer).where(ExamAnswer.session_id == session_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_session_question(
        self, session_id: uuid.UUID, question_id: uuid.UUID
    ) -> ExamAnswer | None:
        stmt = select(ExamAnswer).where(
            ExamAnswer.session_id == session_id,
            ExamAnswer.question_id == question_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
