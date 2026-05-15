from __future__ import annotations

import math
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseSchema(BaseModel):
    """
    Shared Pydantic base schema.

    ``from_attributes=True`` enables ORM mode so SQLAlchemy model instances
    can be passed directly to any schema that inherits from this class.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class PaginatedResponse(BaseSchema, Generic[T]):
    """Generic paginated response envelope used across all list endpoints."""

    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        size: int,
    ) -> "PaginatedResponse[T]":
        pages = math.ceil(total / size) if size > 0 else 0
        return cls(items=items, total=total, page=page, size=size, pages=pages)
