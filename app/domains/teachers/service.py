from __future__ import annotations

import secrets
import uuid

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import get_password_hash
from app.domains.teachers.models import Teacher
from app.domains.teachers.repository import TeacherRepository
from app.domains.teachers.schemas import TeacherCreate, TeacherUpdate
from app.domains.users.models import User
from app.domains.users.repository import UserRepository
from app.shared.enums import UserRole
from app.shared.pagination import PaginationParams


def _normalize_phone(phone: str, dial_code: str = "62") -> str:
    digits = "".join(c for c in phone if c.isdigit())
    if digits.startswith("0"):
        digits = dial_code + digits[1:]
    elif not digits.startswith(dial_code):
        digits = dial_code + digits
    return digits


class TeacherService:
    def __init__(
        self,
        repository: TeacherRepository,
        user_repository: UserRepository | None = None,
    ) -> None:
        self.repository = repository
        self.user_repository = user_repository

    async def _ensure_user_for_phone(
        self,
        phone: str,
        dial_code: str,
        full_name: str,
        tenant_id: uuid.UUID,
    ) -> uuid.UUID:
        """Return user_id for the given phone, creating a TEACHER user if needed."""
        assert self.user_repository is not None
        normalized = _normalize_phone(phone, dial_code)
        existing = await self.user_repository.get_by_phone(normalized, tenant_id)
        if existing is not None:
            return existing.id

        user = User(
            tenant_id=tenant_id,
            email=f"{normalized}@placeholder.local",
            full_name=full_name,
            phone=normalized,
            dial_code=dial_code,
            role=UserRole.TEACHER,
            password_hash=get_password_hash(secrets.token_urlsafe(32)),
            is_active=True,
            is_verified=False,
        )
        self.user_repository.session.add(user)
        await self.user_repository.session.flush()
        await self.user_repository.session.refresh(user)
        return user.id

    async def create_teacher(self, data: TeacherCreate) -> Teacher:
        existing = await self.repository.get_by_nip(data.nip, data.tenant_id)
        if existing is not None:
            raise ConflictError(f"Teacher with NIP '{data.nip}' already exists.")

        teacher_data = data.model_dump(exclude={"phone", "dial_code"})
        teacher_data["phone"] = None

        if data.phone and self.user_repository is not None:
            normalized = _normalize_phone(data.phone, data.dial_code)
            teacher_data["phone"] = normalized
            teacher_data["user_id"] = await self._ensure_user_for_phone(
                data.phone, data.dial_code, data.full_name, data.tenant_id
            )

        teacher = Teacher(**teacher_data)
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

        update_data = data.model_dump(exclude_unset=True, exclude={"phone", "dial_code"})

        if "phone" in data.model_fields_set:
            if data.phone and self.user_repository is not None:
                normalized = _normalize_phone(data.phone, data.dial_code)
                update_data["phone"] = normalized
                # Sync phone on linked user account
                if teacher.user_id is not None:
                    user = await self.user_repository.get(teacher.user_id)
                    if user is not None:
                        user.phone = normalized
                        self.user_repository.session.add(user)
                else:
                    update_data["user_id"] = await self._ensure_user_for_phone(
                        data.phone, data.dial_code, teacher.full_name, tenant_id
                    )
            else:
                update_data["phone"] = data.phone  # None clears it

        for key, value in update_data.items():
            setattr(teacher, key, value)
        self.repository.session.add(teacher)
        await self.repository.session.flush()
        await self.repository.session.refresh(teacher)
        return teacher

    async def delete_teacher(self, teacher_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        teacher = await self.get_or_404(teacher_id, tenant_id)
        return await self.repository.soft_delete(teacher.id)
