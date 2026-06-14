from __future__ import annotations

import uuid

from app.core.exceptions import ConflictError, NotFoundError
from app.domains.subscriptions.models import SubscriptionPackage
from app.domains.subscriptions.repository import SubscriptionPackageRepository
from app.domains.subscriptions.schemas import SubscriptionPackageCreate, SubscriptionPackageUpdate


class SubscriptionService:
    def __init__(self, repo: SubscriptionPackageRepository) -> None:
        self.repo = repo

    async def list_packages(self) -> list[SubscriptionPackage]:
        return await self.repo.list_all()

    async def get_package_or_404(self, package_id: uuid.UUID) -> SubscriptionPackage:
        pkg = await self.repo.get(package_id)
        if pkg is None:
            raise NotFoundError("Subscription package not found.")
        return pkg

    async def create_package(self, data: SubscriptionPackageCreate) -> SubscriptionPackage:
        existing = await self.repo.get_by_plan(data.plan.value)
        if existing:
            raise ConflictError(f"Package for plan '{data.plan}' already exists.")
        pkg = SubscriptionPackage(
            plan=data.plan.value,
            name=data.name,
            description=data.description,
            price_monthly=data.price_monthly,
            price_yearly=data.price_yearly,
            feature_flags=data.feature_flags,
            quota_students=data.quota_students,
            quota_teachers=data.quota_teachers,
            quota_storage_gb=data.quota_storage_gb,
            is_active=data.is_active,
        )
        self.repo.session.add(pkg)
        await self.repo.session.flush()
        await self.repo.session.refresh(pkg)
        return pkg

    async def update_package(
        self, package_id: uuid.UUID, data: SubscriptionPackageUpdate
    ) -> SubscriptionPackage:
        pkg = await self.get_package_or_404(package_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(pkg, field, value)
        await self.repo.session.flush()
        await self.repo.session.refresh(pkg)
        return pkg

    async def delete_package(self, package_id: uuid.UUID) -> None:
        pkg = await self.get_package_or_404(package_id)
        await self.repo.session.delete(pkg)
        await self.repo.session.flush()
