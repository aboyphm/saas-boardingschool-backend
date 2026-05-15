from __future__ import annotations

import io
import uuid

from app.core.exceptions import ConflictError, NotFoundError
from app.domains.students.models import Student
from app.domains.students.repository import StudentRepository
from app.domains.students.schemas import StudentCreate, StudentUpdate
from app.shared.enums import StudentStatus
from app.shared.pagination import PaginationParams


class StudentService:
    def __init__(self, repository: StudentRepository) -> None:
        self.repository = repository

    async def create_student(self, data: StudentCreate) -> Student:
        existing = await self.repository.get_by_nis(data.nis, data.tenant_id)
        if existing is not None:
            raise ConflictError(f"Student with NIS '{data.nis}' already exists.")

        student_dict = data.model_dump()
        student = Student(**student_dict)
        self.repository.session.add(student)
        await self.repository.session.flush()
        await self.repository.session.refresh(student)
        return student

    async def list_students(
        self,
        tenant_id: uuid.UUID,
        pagination: PaginationParams,
        query: str | None = None,
        status: StudentStatus | None = None,
        class_id: uuid.UUID | None = None,
    ) -> tuple[list[Student], int]:
        items = await self.repository.search(
            tenant_id=tenant_id,
            query=query,
            status=status,
            class_id=class_id,
            skip=pagination.offset,
            limit=pagination.size,
        )
        total = await self.repository.count_search(
            tenant_id=tenant_id,
            query=query,
            status=status,
            class_id=class_id,
        )
        return items, total

    async def get_or_404(self, student_id: uuid.UUID, tenant_id: uuid.UUID) -> Student:
        student = await self.repository.get_by_tenant(student_id, tenant_id)
        if student is None:
            raise NotFoundError("Student not found.")
        return student

    async def update_student(
        self,
        student_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: StudentUpdate,
    ) -> Student:
        student = await self.get_or_404(student_id, tenant_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(student, key, value)
        self.repository.session.add(student)
        await self.repository.session.flush()
        await self.repository.session.refresh(student)
        return student

    async def delete_student(self, student_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        student = await self.get_or_404(student_id, tenant_id)
        return await self.repository.soft_delete(student.id)

    async def generate_qr_code(self, student_id: uuid.UUID, tenant_id: uuid.UUID) -> bytes:
        """Generate a QR code PNG containing the student ID."""
        student = await self.get_or_404(student_id, tenant_id)
        try:
            import qrcode

            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(f"student:{student.id}:nis:{student.nis}")
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            return buffer.getvalue()
        except ImportError:
            raise NotFoundError("QR code library not available.")
