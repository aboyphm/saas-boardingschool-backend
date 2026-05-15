from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import redis.asyncio as aioredis

from app.core.config import get_settings

settings = get_settings()

# ─── Shared async Redis client ────────────────────────────────────────────────
_redis_pool: aioredis.Redis | None = None


async def get_redis_pool() -> aioredis.Redis:
    """Return (or create) the shared async Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    return _redis_pool


async def close_redis_pool() -> None:
    """Close the Redis connection pool on application shutdown."""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.aclose()
        _redis_pool = None


# ─── FastAPI dependency ───────────────────────────────────────────────────────
async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """Yield the Redis client as a FastAPI dependency."""
    client = await get_redis_pool()
    yield client


# ─── High-level Redis wrapper ─────────────────────────────────────────────────
class RedisClient:
    """
    Thin async wrapper around the Redis client providing namespaced operations.

    All keys are prefixed with ``app:`` to avoid collisions with other
    applications sharing the same Redis instance.
    """

    PREFIX = "app"

    def __init__(self, client: aioredis.Redis) -> None:
        self._client = client

    def _key(self, key: str) -> str:
        return f"{self.PREFIX}:{key}"

    async def get(self, key: str) -> str | None:
        return await self._client.get(self._key(key))

    async def set(
        self,
        key: str,
        value: str,
        expire: int | None = None,
    ) -> bool:
        return await self._client.set(self._key(key), value, ex=expire)

    async def delete(self, key: str) -> int:
        return await self._client.delete(self._key(key))

    async def exists(self, key: str) -> bool:
        result: int = await self._client.exists(self._key(key))
        return bool(result)

    async def expire(self, key: str, seconds: int) -> bool:
        return await self._client.expire(self._key(key), seconds)

    async def hget(self, name: str, field: str) -> str | None:
        return await self._client.hget(self._key(name), field)

    async def hset(self, name: str, field: str, value: str) -> int:
        return await self._client.hset(self._key(name), field, value)

    async def hgetall(self, name: str) -> dict[str, Any]:
        return await self._client.hgetall(self._key(name))

    async def lpush(self, name: str, *values: str) -> int:
        return await self._client.lpush(self._key(name), *values)

    async def rpop(self, name: str) -> str | None:
        return await self._client.rpop(self._key(name))

    async def incr(self, key: str, amount: int = 1) -> int:
        return await self._client.incrby(self._key(key), amount)

    async def keys(self, pattern: str) -> list[str]:
        """Return all keys matching a glob-style pattern (use with caution)."""
        return await self._client.keys(self._key(pattern))
