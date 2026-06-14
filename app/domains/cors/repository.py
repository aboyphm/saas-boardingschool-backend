from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.cors.models import CorsOrigin
from app.domains.cors.schemas import CorsOriginCreate
from app.shared.base_repository import BaseRepository


class CorsOriginRepository(BaseRepository[CorsOrigin, CorsOriginCreate, CorsOriginCreate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CorsOrigin, session)

    async def list_all(self) -> list[CorsOrigin]:
        stmt = select(CorsOrigin).order_by(CorsOrigin.created_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_active(self) -> list[CorsOrigin]:
        stmt = select(CorsOrigin).where(CorsOrigin.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_origin(self, origin: str) -> CorsOrigin | None:
        stmt = select(CorsOrigin).where(CorsOrigin.origin == origin)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
