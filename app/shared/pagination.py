from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Query


@dataclass
class PaginationParams:
    """
    Standard pagination parameters injected as a FastAPI dependency.

    Usage::

        @router.get("/items")
        async def list_items(pagination: PaginationParams = Depends()):
            ...
    """

    page: int = field(default=1)
    size: int = field(default=20)

    # Maximum page size enforced regardless of what the client requests.
    max_size: int = field(default=100, repr=False)

    def __post_init__(self) -> None:
        if self.page < 1:
            self.page = 1
        if self.size < 1:
            self.size = 1
        if self.size > self.max_size:
            self.size = self.max_size

    @property
    def offset(self) -> int:
        """Calculate the SQL OFFSET value from page and size."""
        return (self.page - 1) * self.size


def get_pagination_params(
    page: int = Query(default=1, ge=1, description="Page number, starting at 1"),
    size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
) -> PaginationParams:
    """
    FastAPI dependency that parses and validates pagination query parameters.

    Inject via ``pagination: PaginationParams = Depends(get_pagination_params)``.
    """
    return PaginationParams(page=page, size=size)
