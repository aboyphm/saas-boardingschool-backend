from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

# ─── Engine ───────────────────────────────────────────────────────────────────
async_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,          # Verify connections before use
    pool_recycle=3600,           # Recycle connections after 1 hour
    echo=settings.DEBUG,         # Log SQL only in debug mode
)

# ─── Session factory ──────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,      # Avoid lazy-load errors after commit
    autoflush=False,
    autocommit=False,
)


# ─── Declarative base ─────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """Shared declarative base for all SQLAlchemy models."""
    pass


# ─── FastAPI dependency ───────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async database session for use as a FastAPI dependency.

    The session is always closed in the finally block regardless of whether
    the request succeeds or raises an exception.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ─── Context manager ──────────────────────────────────────────────────────────
@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions outside the request lifecycle.

    Usage::

        async with get_db_session() as session:
            result = await session.execute(select(User))
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
