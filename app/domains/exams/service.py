from __future__ import annotations

import random
import statistics
import uuid
from datetime import datetime, timedelta, timezone

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.domains.exams.models import (
    Exam, ExamAnswer, ExamQuestion, ExamQuestionMap, ExamSession,
)
from app.domains.exams.repository import (
    ExamAnswerRepository,
    ExamQuestionMapRepository,
    ExamQuestionRepository,
    ExamRepository,
    ExamSessionRepository,
)
from app.domains.exams.schemas import (
    AnswerRequest,
    ExamCreate,
    ExamUpdate,
    GradeEssaysRequest,
    QuestionCreate,
    QuestionUpdate,
    ResultsResponse,
    ResultSummary,
)


def _grade_letter(score: float) -> str:
    if score >= 90: return "A"
    if score >= 80: return "B+"
    if score >= 70: return "B"
    if score >= 60: return "C+"
    if score >= 50: return "C"
    return "D"


class ExamsService:
    def __init__(
        self,
        question_repo: ExamQuestionRepository,
        exam_repo: ExamRepository,
        map_repo: ExamQuestionMapRepository,
        session_repo: ExamSessionRepository,
        answer_repo: ExamAnswerRepository,
    ) -> None:
        self.question_repo = question_repo
        self.exam_repo = exam_repo
        self.map_repo = map_repo
        self.session_repo = session_repo
        self.answer_repo = answer_repo

    # ── Question Bank ──────────────────────────────────────────────────────────

    async def list_questions(
        self,
        tenant_id: uuid.UUID,
        subject_id: uuid.UUID | None = None,
        grade_level: str | None = None,
        category: str | None = None,
        question_type: str | None = None,
    ) -> list[ExamQuestion]:
        return await self.question_repo.list_by_tenant(
            tenant_id, subject_id, grade_level, category, question_type
        )

    async def create_question(
        self, data: QuestionCreate, tenant_id: uuid.UUID, teacher_id: uuid.UUID | None = None
    ) -> ExamQuestion:
        q = ExamQuestion(
            tenant_id=tenant_id,
            created_by=teacher_id,
            **data.model_dump(),
        )
        self.question_repo.session.add(q)
        await self.question_repo.session.flush()
        await self.question_repo.session.refresh(q)
        return q

    async def update_question(
        self, question_id: uuid.UUID, data: QuestionUpdate, tenant_id: uuid.UUID
    ) -> ExamQuestion:
        q = await self.question_repo.get_by_tenant(question_id, tenant_id)
        if q is None:
            raise NotFoundError("Question not found.")
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(q, field, value)
        await self.question_repo.session.flush()
        await self.question_repo.session.refresh(q)
        return q

    async def delete_question(self, question_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        q = await self.question_repo.get_by_tenant(question_id, tenant_id)
        if q is None:
            raise NotFoundError("Question not found.")
        await self.question_repo.session.delete(q)
        await self.question_repo.session.flush()

    # ── Exam Management ────────────────────────────────────────────────────────

    async def list_exams(
        self,
        tenant_id: uuid.UUID,
        class_id: uuid.UUID | None = None,
        academic_year_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> list[Exam]:
        return await self.exam_repo.list_by_tenant(tenant_id, class_id, academic_year_id, status)

    async def get_exam_or_404(self, exam_id: uuid.UUID, tenant_id: uuid.UUID) -> Exam:
        exam = await self.exam_repo.get_by_tenant(exam_id, tenant_id)
        if exam is None:
            raise NotFoundError("Exam not found.")
        return exam

    async def create_exam(self, data: ExamCreate, tenant_id: uuid.UUID) -> Exam:
        exam = Exam(tenant_id=tenant_id, **data.model_dump())
        self.exam_repo.session.add(exam)
        await self.exam_repo.session.flush()
        await self.exam_repo.session.refresh(exam)
        return exam

    async def update_exam(
        self, exam_id: uuid.UUID, data: ExamUpdate, tenant_id: uuid.UUID
    ) -> Exam:
        exam = await self.get_exam_or_404(exam_id, tenant_id)
        if exam.status not in ("DRAFT", "PUBLISHED"):
            raise ConflictError("Only DRAFT or PUBLISHED exams can be edited.")
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(exam, field, value)
        await self.exam_repo.session.flush()
        await self.exam_repo.session.refresh(exam)
        return exam

    async def delete_exam(self, exam_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        exam = await self.get_exam_or_404(exam_id, tenant_id)
        if exam.status not in ("DRAFT",):
            raise ConflictError("Only DRAFT exams can be deleted.")
        await self.exam_repo.session.delete(exam)
        await self.exam_repo.session.flush()

    async def _transition(self, exam_id: uuid.UUID, tenant_id: uuid.UUID, from_: str, to: str) -> Exam:
        exam = await self.get_exam_or_404(exam_id, tenant_id)
        if exam.status != from_:
            raise ConflictError(f"Exam must be {from_} to transition to {to}.")
        exam.status = to
        await self.exam_repo.session.flush()
        await self.exam_repo.session.refresh(exam)
        return exam

    async def publish_exam(self, exam_id: uuid.UUID, tenant_id: uuid.UUID) -> Exam:
        return await self._transition(exam_id, tenant_id, "DRAFT", "PUBLISHED")

    async def activate_exam(self, exam_id: uuid.UUID, tenant_id: uuid.UUID) -> Exam:
        return await self._transition(exam_id, tenant_id, "PUBLISHED", "ACTIVE")

    async def complete_exam(self, exam_id: uuid.UUID, tenant_id: uuid.UUID) -> Exam:
        exam = await self.get_exam_or_404(exam_id, tenant_id)
        if exam.status != "ACTIVE":
            raise ConflictError("Exam must be ACTIVE to complete.")
        sessions = await self.session_repo.list_by_exam(exam_id)
        for s in sessions:
            if s.status == "IN_PROGRESS":
                await self._do_submit(s, exam)
        exam.status = "COMPLETED"
        await self.exam_repo.session.flush()
        await self.exam_repo.session.refresh(exam)
        return exam

    # ── Exam Question Map ──────────────────────────────────────────────────────

    async def list_exam_questions(self, exam_id: uuid.UUID, tenant_id: uuid.UUID) -> list[ExamQuestion]:
        await self.get_exam_or_404(exam_id, tenant_id)
        maps = await self.map_repo.list_by_exam(exam_id)
        questions = []
        for m in maps:
            q = await self.question_repo.session.get(ExamQuestion, m.question_id)
            if q:
                questions.append(q)
        return questions

    async def add_question_to_exam(
        self, exam_id: uuid.UUID, question_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> ExamQuestionMap:
        await self.get_exam_or_404(exam_id, tenant_id)
        existing = await self.map_repo.get_by_exam_question(exam_id, question_id)
        if existing:
            raise ConflictError("Question already in exam.")
        maps = await self.map_repo.list_by_exam(exam_id)
        order = (max(m.display_order for m in maps) + 1) if maps else 1
        mapping = ExamQuestionMap(
            exam_id=exam_id,
            question_id=question_id,
            display_order=order,
        )
        self.map_repo.session.add(mapping)
        await self.map_repo.session.flush()
        await self.map_repo.session.refresh(mapping)
        return mapping

    async def remove_question_from_exam(
        self, exam_id: uuid.UUID, question_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        await self.get_exam_or_404(exam_id, tenant_id)
        mapping = await self.map_repo.get_by_exam_question(exam_id, question_id)
        if mapping is None:
            raise NotFoundError("Question not in exam.")
        await self.map_repo.session.delete(mapping)
        await self.map_repo.session.flush()

    # ── Session (Student CBT) ──────────────────────────────────────────────────

    async def start_session(
        self, exam_id: uuid.UUID, student_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> ExamSession:
        exam = await self.get_exam_or_404(exam_id, tenant_id)
        if exam.status != "ACTIVE":
            raise ConflictError("Ujian belum dimulai atau sudah selesai")
        existing = await self.session_repo.get_by_exam_student(exam_id, student_id)
        if existing:
            raise ConflictError("Anda sudah memulai ujian ini")

        maps = await self.map_repo.list_by_exam(exam_id)
        question_ids = [str(m.question_id) for m in maps]

        shuffled_ids = question_ids[:]
        if exam.shuffle_questions:
            for i in range(len(shuffled_ids) - 1, 0, -1):
                j = random.randint(0, i)
                shuffled_ids[i], shuffled_ids[j] = shuffled_ids[j], shuffled_ids[i]

        option_maps: dict[str, list[int]] = {}
        for qid_str in shuffled_ids:
            q = await self.question_repo.session.get(ExamQuestion, uuid.UUID(qid_str))
            if q and q.question_type == "MCQ" and q.options and exam.shuffle_options:
                indices = list(range(len(q.options)))
                random.shuffle(indices)
                option_maps[qid_str] = indices
            else:
                num_opts = len(q.options) if q and q.options else 4
                option_maps[qid_str] = list(range(num_opts))

        now = datetime.now(timezone.utc)
        session = ExamSession(
            tenant_id=tenant_id,
            exam_id=exam_id,
            student_id=student_id,
            started_at=now,
            shuffled_ids=shuffled_ids,
            option_maps=option_maps,
        )
        self.session_repo.session.add(session)
        await self.session_repo.session.flush()
        await self.session_repo.session.refresh(session)

        for qid_str in shuffled_ids:
            answer = ExamAnswer(
                session_id=session.id,
                question_id=uuid.UUID(qid_str),
            )
            self.answer_repo.session.add(answer)
        await self.answer_repo.session.flush()

        return session

    async def get_session(
        self, session_id: uuid.UUID, tenant_id: uuid.UUID, student_id: uuid.UUID | None = None
    ) -> tuple[ExamSession, list[ExamQuestion]]:
        session = await self.session_repo.session.get(ExamSession, session_id)
        if session is None or session.tenant_id != tenant_id:
            raise NotFoundError("Session not found.")
        if student_id is not None and session.student_id != student_id:
            raise ForbiddenError("You can only access your own exam session.")
        questions = []
        for qid_str in session.shuffled_ids:
            q = await self.question_repo.session.get(ExamQuestion, uuid.UUID(qid_str))
            if q:
                questions.append(q)
        return session, questions

    async def save_answer(
        self,
        session_id: uuid.UUID,
        data: AnswerRequest,
        tenant_id: uuid.UUID,
        student_id: uuid.UUID | None = None,
    ) -> ExamAnswer:
        session = await self.session_repo.session.get(ExamSession, session_id)
        if session is None or session.tenant_id != tenant_id:
            raise NotFoundError("Session not found.")
        if student_id is not None and session.student_id != student_id:
            raise ForbiddenError("You can only access your own exam session.")

        exam = await self.exam_repo.session.get(Exam, session.exam_id)
        started = session.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        deadline = started + timedelta(minutes=exam.duration_minutes)
        if datetime.now(timezone.utc) > deadline:
            raise ConflictError("Waktu ujian sudah habis")

        answer = await self.answer_repo.get_by_session_question(session_id, data.question_id)
        if answer is None:
            raise NotFoundError("Answer slot not found.")
        answer.selected_option = data.selected_option
        answer.essay_text = data.essay_text
        await self.answer_repo.session.flush()
        return answer

    async def _do_submit(self, session: ExamSession, exam: Exam) -> None:
        answers = await self.answer_repo.list_by_session(session.id)
        has_essay = False
        score_mcq = 0.0

        for answer in answers:
            q = await self.question_repo.session.get(ExamQuestion, answer.question_id)
            if q is None:
                continue
            if q.question_type == "MCQ" and answer.selected_option is not None:
                om = session.option_maps.get(str(answer.question_id), [])
                original_idx = om[answer.selected_option] if om and answer.selected_option < len(om) else answer.selected_option
                is_correct = (original_idx == q.correct_option)
                answer.is_correct = is_correct
                answer.points_earned = float(q.points) if is_correct else 0.0
                if is_correct:
                    score_mcq += q.points
            elif q.question_type == "ESSAY":
                has_essay = True

        session.score_mcq = score_mcq
        session.submitted_at = datetime.now(timezone.utc)
        if has_essay:
            session.status = "SUBMITTED"
        else:
            session.total_score = score_mcq
            session.status = "GRADED"

    async def submit_session(
        self, session_id: uuid.UUID, tenant_id: uuid.UUID, student_id: uuid.UUID | None = None
    ) -> ExamSession:
        session = await self.session_repo.session.get(ExamSession, session_id)
        if session is None or session.tenant_id != tenant_id:
            raise NotFoundError("Session not found.")
        if student_id is not None and session.student_id != student_id:
            raise ForbiddenError("You can only access your own exam session.")
        if session.status != "IN_PROGRESS":
            raise ConflictError("Session already submitted.")
        exam = await self.exam_repo.session.get(Exam, session.exam_id)
        await self._do_submit(session, exam)
        await self.session_repo.session.flush()
        return session

    async def get_session_result(
        self, session_id: uuid.UUID, tenant_id: uuid.UUID, student_id: uuid.UUID | None = None
    ) -> ExamSession:
        session = await self.session_repo.session.get(ExamSession, session_id)
        if session is None or session.tenant_id != tenant_id:
            raise NotFoundError("Session not found.")
        if student_id is not None and session.student_id != student_id:
            raise ForbiddenError("You can only access your own exam session.")
        if session.status not in ("GRADED",):
            raise ConflictError("Results not yet available.")
        return session

    # ── Essay Grading ──────────────────────────────────────────────────────────

    async def list_ungraded_sessions(
        self, exam_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> list[dict]:
        await self.get_exam_or_404(exam_id, tenant_id)
        sessions = await self.session_repo.list_submitted_by_exam(exam_id)
        result = []
        for s in sessions:
            answers = await self.answer_repo.list_by_session(s.id)
            essay_answers = []
            for a in answers:
                q = await self.question_repo.session.get(ExamQuestion, a.question_id)
                if q and q.question_type == "ESSAY" and a.points_earned is None:
                    essay_answers.append({
                        "question_id": str(a.question_id),
                        "body": q.body,
                        "essay_text": a.essay_text,
                        "max_points": q.points,
                    })
            if essay_answers:
                from app.domains.students.models import Student
                student = await self.session_repo.session.get(Student, s.student_id)
                result.append({
                    "session_id": str(s.id),
                    "student_name": student.full_name if student else str(s.student_id),
                    "essay_answers": essay_answers,
                })
        return result

    async def grade_essays(
        self,
        session_id: uuid.UUID,
        data: GradeEssaysRequest,
        teacher_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> ExamSession:
        session = await self.session_repo.session.get(ExamSession, session_id)
        if session is None or session.tenant_id != tenant_id:
            raise NotFoundError("Session not found.")

        now = datetime.now(timezone.utc)
        for item in data.grades:
            answer = await self.answer_repo.get_by_session_question(session_id, item.question_id)
            if answer:
                answer.points_earned = item.points_earned
                answer.graded_by = teacher_id
                answer.graded_at = now

        answers = await self.answer_repo.list_by_session(session_id)
        all_graded = all(
            a.points_earned is not None or (a.selected_option is None and a.essay_text is None)
            for a in answers
        )
        if all_graded:
            essay_score = sum(
                a.points_earned or 0
                for a in answers
                if a.essay_text is not None or a.graded_at is not None
            )
            session.score_essay = essay_score
            session.total_score = (session.score_mcq or 0) + essay_score
            session.status = "GRADED"

        await self.session_repo.session.flush()
        return session

    # ── Results & Analytics ────────────────────────────────────────────────────

    async def get_results(self, exam_id: uuid.UUID, tenant_id: uuid.UUID) -> ResultsResponse:
        await self.get_exam_or_404(exam_id, tenant_id)
        sessions = await self.session_repo.list_by_exam(exam_id)
        graded = [s for s in sessions if s.status == "GRADED" and s.total_score is not None]

        scores = [s.total_score for s in graded]
        exam = await self.exam_repo.session.get(Exam, exam_id)
        passing = exam.passing_score if exam else 60

        summary = ResultSummary(
            mean=round(statistics.mean(scores), 2) if scores else 0.0,
            median=round(statistics.median(scores), 2) if scores else 0.0,
            highest=max(scores) if scores else 0.0,
            lowest=min(scores) if scores else 0.0,
            pass_rate=round(len([s for s in scores if s >= passing]) / len(scores) * 100, 2) if scores else 0.0,
            total_students=len(graded),
        )

        distribution = {"0-49": 0, "50-59": 0, "60-69": 0, "70-79": 0, "80-89": 0, "90+": 0}
        for sc in scores:
            if sc >= 90: distribution["90+"] += 1
            elif sc >= 80: distribution["80-89"] += 1
            elif sc >= 70: distribution["70-79"] += 1
            elif sc >= 60: distribution["60-69"] += 1
            elif sc >= 50: distribution["50-59"] += 1
            else: distribution["0-49"] += 1

        maps = await self.map_repo.list_by_exam(exam_id)
        per_question = []
        for m in maps:
            q = await self.question_repo.session.get(ExamQuestion, m.question_id)
            if not q:
                continue
            all_answers = []
            for s in graded:
                a = await self.answer_repo.get_by_session_question(s.id, q.id)
                if a:
                    all_answers.append(a)
            if q.question_type == "MCQ":
                correct_count = sum(1 for a in all_answers if a.is_correct)
                correct_rate = round(correct_count / len(all_answers) * 100, 2) if all_answers else 0.0
                per_question.append({
                    "question_id": str(q.id),
                    "body_preview": q.body[:80],
                    "correct_rate": correct_rate,
                    "avg_score": None,
                })
            else:
                earned = [a.points_earned for a in all_answers if a.points_earned is not None]
                avg = round(statistics.mean(earned), 2) if earned else 0.0
                per_question.append({
                    "question_id": str(q.id),
                    "body_preview": q.body[:80],
                    "correct_rate": None,
                    "avg_score": avg,
                })

        per_question.sort(key=lambda x: x["correct_rate"] if x["correct_rate"] is not None else (x["avg_score"] or 0))

        student_rows = []
        for i, s in enumerate(sorted(graded, key=lambda x: x.total_score, reverse=True), 1):
            from app.domains.students.models import Student
            student = await self.session_repo.session.get(Student, s.student_id)
            student_rows.append({
                "rank": i,
                "student_id": str(s.student_id),
                "student_name": student.full_name if student else str(s.student_id),
                "score_mcq": s.score_mcq,
                "score_essay": s.score_essay,
                "total_score": s.total_score,
                "grade_letter": _grade_letter(s.total_score),
                "status": s.status,
            })

        return ResultsResponse(
            summary=summary,
            distribution=distribution,
            per_question=per_question[:5],
            students=student_rows,
        )
