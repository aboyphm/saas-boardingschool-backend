from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.dormitory.models import (
    DormitoryAssignment,
    DormitoryBuilding,
    DormitoryRoom,
    DormitorySupervisor,
)
from app.domains.dormitory.schemas import (
    DormitoryAssignmentCreate,
    DormitoryBuildingCreate,
    DormitoryBuildingUpdate,
    DormitoryRoomCreate,
    DormitoryRoomUpdate,
)
from app.shared.base_repository import BaseRepository
from app.shared.enums import DormitoryRoomStatus


class DormitoryBuildingRepository(
    BaseRepository[DormitoryBuilding, DormitoryBuildingCreate, DormitoryBuildingUpdate]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DormitoryBuilding, session)

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[DormitoryBuilding]:
        stmt = (
            select(DormitoryBuilding)
            .where(DormitoryBuilding.tenant_id == tenant_id)
            .order_by(DormitoryBuilding.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class DormitoryRoomRepository(
    BaseRepository[DormitoryRoom, DormitoryRoomCreate, DormitoryRoomUpdate]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DormitoryRoom, session)

    async def list_by_building(
        self, building_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> list[DormitoryRoom]:
        stmt = (
            select(DormitoryRoom)
            .where(
                DormitoryRoom.building_id == building_id,
                DormitoryRoom.tenant_id == tenant_id,
            )
            .order_by(DormitoryRoom.room_number)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_available_rooms(self, tenant_id: uuid.UUID) -> list[DormitoryRoom]:
        stmt = (
            select(DormitoryRoom)
            .where(
                DormitoryRoom.tenant_id == tenant_id,
                DormitoryRoom.status == DormitoryRoomStatus.AVAILABLE,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class DormitoryAssignmentRepository(
    BaseRepository[DormitoryAssignment, DormitoryAssignmentCreate, dict]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DormitoryAssignment, session)

    async def get_active_by_student(
        self, student_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> DormitoryAssignment | None:
        stmt = (
            select(DormitoryAssignment)
            .where(
                DormitoryAssignment.student_id == student_id,
                DormitoryAssignment.tenant_id == tenant_id,
                DormitoryAssignment.is_active.is_(True),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
