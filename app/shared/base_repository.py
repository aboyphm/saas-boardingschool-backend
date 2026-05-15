from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.base_model import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Generic async CRUD repository built on SQLAlchemy 2.0.

    All queries automatically exclude soft-deleted records when the model
    carries the ``is_deleted`` attribute from :class:`SoftDeleteMixin`.
    """

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    def _base_query(self):
        """Return a base select statement, filtering soft-deleted rows if applicable."""
        stmt = select(self.model)
        if hasattr(self.model, "is_deleted"):
            stmt = stmt.where(self.model.is_deleted.is_(False))
        return stmt

    async def get(self, record_id: uuid.UUID) -> ModelType | None:
        """Fetch a single record by its primary key."""
        stmt = self._base_query().where(self.model.id == record_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_tenant(
        self,
        record_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> ModelType | None:
        """Fetch a record by primary key, scoped to the given tenant."""
        stmt = (
            self._base_query()
            .where(self.model.id == record_id)
            .where(self.model.tenant_id == tenant_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 20,
        order_by: Any = None,
    ) -> list[ModelType]:
        """Return a paginated list of records, optionally filtered."""
        stmt = self._base_query()

        if filters:
            for attr, value in filters.items():
                if hasattr(self.model, attr) and value is not None:
                    stmt = stmt.where(getattr(self.model, attr) == value)

        if order_by is not None:
            stmt = stmt.order_by(order_by)
        else:
            stmt = stmt.order_by(self.model.created_at.desc())

        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        """Persist a new record and return the populated instance."""
        if hasattr(obj_in, "model_dump"):
            data = obj_in.model_dump(exclude_unset=False)
        else:
            data = dict(obj_in)

        db_obj = self.model(**data)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(
        self,
        record_id: uuid.UUID,
        obj_in: UpdateSchemaType,
    ) -> ModelType | None:
        """Update an existing record with only the supplied fields."""
        db_obj = await self.get(record_id)
        if db_obj is None:
            return None

        if hasattr(obj_in, "model_dump"):
            update_data = obj_in.model_dump(exclude_unset=True)
        else:
            update_data = {k: v for k, v in dict(obj_in).items() if v is not None}

        for field_name, value in update_data.items():
            setattr(db_obj, field_name, value)

        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def soft_delete(self, record_id: uuid.UUID) -> bool:
        """Mark a record as deleted without removing it from the database."""
        from datetime import UTC, datetime

        db_obj = await self.get(record_id)
        if db_obj is None:
            return False

        db_obj.is_deleted = True
        db_obj.deleted_at = datetime.now(UTC)
        self.session.add(db_obj)
        await self.session.flush()
        return True

    async def hard_delete(self, record_id: uuid.UUID) -> bool:
        """Permanently remove a record from the database."""
        db_obj = await self.get(record_id)
        if db_obj is None:
            return False

        await self.session.delete(db_obj)
        await self.session.flush()
        return True

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Return the total count of records matching the given filters."""
        stmt = select(func.count()).select_from(self.model)

        if hasattr(self.model, "is_deleted"):
            stmt = stmt.where(self.model.is_deleted.is_(False))

        if filters:
            for attr, value in filters.items():
                if hasattr(self.model, attr) and value is not None:
                    stmt = stmt.where(getattr(self.model, attr) == value)

        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def exists(self, filters: dict[str, Any]) -> bool:
        """Return True if at least one record matches the given filters."""
        stmt = select(func.count()).select_from(self.model)

        if hasattr(self.model, "is_deleted"):
            stmt = stmt.where(self.model.is_deleted.is_(False))

        for attr, value in filters.items():
            if hasattr(self.model, attr):
                stmt = stmt.where(getattr(self.model, attr) == value)

        result = await self.session.execute(stmt)
        return result.scalar_one() > 0
