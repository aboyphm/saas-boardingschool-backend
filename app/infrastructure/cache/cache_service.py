from __future__ import annotations

import json
import uuid
from typing import Any

import redis.asyncio as aioredis

from app.core.redis import get_redis_pool


class CacheService:
    """
    Application-level cache service with namespaced Redis keys.

    All methods are async and handle serialisation/deserialisation internally.
    Cache TTLs are chosen to balance freshness with performance.
    """

    # TTL constants (seconds)
    TENANT_SETTINGS_TTL = 3600       # 1 hour
    USER_PERMISSIONS_TTL = 900       # 15 minutes
    STUDENT_LIST_TTL = 300           # 5 minutes

    @staticmethod
    async def _get_client() -> aioredis.Redis:
        return await get_redis_pool()

    # ─── Tenant settings ──────────────────────────────────────────────────────
    async def get_tenant_settings(self, tenant_id: uuid.UUID) -> dict | None:
        """Return cached tenant settings, or None on a cache miss."""
        client = await self._get_client()
        raw = await client.get(f"tenant:{tenant_id}:settings")
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    async def set_tenant_settings(self, tenant_id: uuid.UUID, settings: dict) -> None:
        """Cache tenant settings for TENANT_SETTINGS_TTL seconds."""
        client = await self._get_client()
        await client.setex(
            f"tenant:{tenant_id}:settings",
            self.TENANT_SETTINGS_TTL,
            json.dumps(settings),
        )

    async def invalidate_tenant_cache(self, tenant_id: uuid.UUID) -> None:
        """Evict all cache entries for the given tenant."""
        client = await self._get_client()
        pattern = f"tenant:{tenant_id}:*"
        keys = await client.keys(pattern)
        if keys:
            await client.delete(*keys)

    # ─── User permissions ─────────────────────────────────────────────────────
    async def cache_user_permissions(
        self, user_id: uuid.UUID, permissions: list[str]
    ) -> None:
        """Cache the list of permissions for a user."""
        client = await self._get_client()
        await client.setex(
            f"user:{user_id}:permissions",
            self.USER_PERMISSIONS_TTL,
            json.dumps(permissions),
        )

    async def get_user_permissions(self, user_id: uuid.UUID) -> list[str] | None:
        """Return cached user permissions, or None on a cache miss."""
        client = await self._get_client()
        raw = await client.get(f"user:{user_id}:permissions")
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    async def invalidate_user_permissions(self, user_id: uuid.UUID) -> None:
        """Evict the permissions cache for a specific user."""
        client = await self._get_client()
        await client.delete(f"user:{user_id}:permissions")

    # ─── Generic helpers ──────────────────────────────────────────────────────
    async def get_json(self, key: str) -> Any | None:
        """Generic JSON get."""
        client = await self._get_client()
        raw = await client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    async def set_json(self, key: str, value: Any, ttl: int = 300) -> None:
        """Generic JSON set with TTL."""
        client = await self._get_client()
        await client.setex(key, ttl, json.dumps(value, default=str))
