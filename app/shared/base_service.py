from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from app.shared.base_repository import BaseRepository
from app.shared.base_model import BaseModel
from app.core.exceptions import NotFoundError
from app.shared.pagination import PaginationParams

ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")
RepositoryType = TypeVar("RepositoryType", bound=BaseRepository)


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Generic service base class that delegates standard CRUD operations to the
    underlying repository.

    Domain-specific services should inherit from this class and add business
    logic around the CRUD methods as needed.
    """

    def __init__(
        self,
        repository: BaseRepository[ModelType, CreateSchemaType, UpdateSchemaType],
    ) -> None:
        self.repository = repository

    async def get_or_404(self, record_id: uuid.UUID) -> ModelType:
        """Fetch a record by ID or raise :class:`NotFoundError`."""
        obj = await self.repository.get(record_id)
        if obj is None:
            raise NotFoundError(f"Record with id={record_id} was not found.")
        return obj

    async def get_by_tenant_or_404(
        self,
        record_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> ModelType:
        """Fetch a tenant-scoped record by ID or raise :class:`NotFoundError`."""
        obj = await self.repository.get_by_tenant(record_id, tenant_id)
        if obj is None:
            raise NotFoundError(f"Record with id={record_id} was not found.")
        return obj

    async def list(
        self,
        pagination: PaginationParams,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[ModelType], int]:
        """Return a paginated list of records alongside the total count."""
        items = await self.repository.list(
            filters=filters,
            skip=pagination.offset,
            limit=pagination.size,
        )
        total = await self.repository.count(filters=filters)
        return items, total

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        return await self.repository.create(obj_in)

    async def update(
        self,
        record_id: uuid.UUID,
        obj_in: UpdateSchemaType,
    ) -> ModelType:
        obj = await self.repository.update(record_id, obj_in)
        if obj is None:
            raise NotFoundError(f"Record with id={record_id} was not found.")
        return obj

    async def delete(self, record_id: uuid.UUID) -> bool:
        """Soft-delete a record. Returns False if the record did not exist."""
        return await self.repository.soft_delete(record_id)
