from __future__ import annotations

import uuid

from app.core.exceptions import ConflictError, NotFoundError
from app.domains.teachers.models import Teacher
from app.domains.teachers.repository import TeacherRepository
from app.domains.teachers.schemas import TeacherCreate, TeacherUpdate
from app.shared.pagination import PaginationParams


class TeacherService:
    def __init__(self, repository: TeacherRepository) -> None:
        self.repository = repository

    async def create_teacher(self, data: TeacherCreate) -> Teacher:
        existing = await self.repository.get_by_nip(data.nip, data.tenant_id)
        if existing is not None:
            raise ConflictError(f"Teacher with NIP '{data.nip}' already exists.")

        teacher = Teacher(**data.model_dump())
        self.repository.session.add(teacher)
        await self.repository.session.flush()
        await self.repository.session.refresh(teacher)
        return teacher

    async def list_teachers(
        self,
        tenant_id: uuid.UUID,
        pagination: PaginationParams,
        query: str | None = None,
    ) -> tuple[list[Teacher], int]:
        items = await self.repository.search(
            tenant_id=tenant_id,
            query=query,
            skip=pagination.offset,
            limit=pagination.size,
        )
        total = await self.repository.count(filters={"tenant_id": tenant_id})
        return items, total

    async def get_or_404(self, teacher_id: uuid.UUID, tenant_id: uuid.UUID) -> Teacher:
        teacher = await self.repository.get_by_tenant(teacher_id, tenant_id)
        if teacher is None:
            raise NotFoundError("Teacher not found.")
        return teacher

    async def update_teacher(
        self,
        teacher_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: TeacherUpdate,
    ) -> Teacher:
        teacher = await self.get_or_404(teacher_id, tenant_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(teacher, key, value)
        self.repository.session.add(teacher)
        await self.repository.session.flush()
        await self.repository.session.refresh(teacher)
        return teacher

    async def delete_teacher(self, teacher_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        teacher = await self.get_or_404(teacher_id, tenant_id)
        return await self.repository.soft_delete(teacher.id)
