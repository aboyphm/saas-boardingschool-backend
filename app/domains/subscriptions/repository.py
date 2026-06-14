from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.subscriptions.models import SubscriptionPackage
from app.domains.subscriptions.schemas import SubscriptionPackageCreate, SubscriptionPackageUpdate
from app.shared.base_repository import BaseRepository


class SubscriptionPackageRepository(
    BaseRepository[SubscriptionPackage, SubscriptionPackageCreate, SubscriptionPackageUpdate]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(SubscriptionPackage, session)

    async def list_all(self) -> list[SubscriptionPackage]:
        stmt = select(SubscriptionPackage).order_by(SubscriptionPackage.created_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_plan(self, plan: str) -> SubscriptionPackage | None:
        stmt = select(SubscriptionPackage).where(SubscriptionPackage.plan == plan)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
