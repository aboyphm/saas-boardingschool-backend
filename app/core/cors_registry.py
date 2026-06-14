"""In-memory CORS origin registry — loaded at startup, hot-updated via API."""
from __future__ import annotations

_allowed: set[str] = set()


def get_allowed() -> frozenset[str]:
    return frozenset(_allowed)


def set_origins(origins: set[str]) -> None:
    global _allowed
    _allowed = origins


def add_origin(origin: str) -> None:
    _allowed.add(origin)


def remove_origin(origin: str) -> None:
    _allowed.discard(origin)
