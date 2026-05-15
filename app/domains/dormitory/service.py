from __future__ import annotations

import uuid
from datetime import date

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domains.dormitory.models import DormitoryAssignment, DormitoryBuilding, DormitoryRoom
from app.domains.dormitory.repository import (
    DormitoryAssignmentRepository,
    DormitoryBuildingRepository,
    DormitoryRoomRepository,
)
from app.domains.dormitory.schemas import (
    DormitoryAssignmentCreate,
    DormitoryBuildingCreate,
    DormitoryBuildingUpdate,
    DormitoryRoomCreate,
    DormitoryRoomUpdate,
)
from app.shared.enums import DormitoryRoomStatus


class DormitoryService:
    def __init__(
        self,
        building_repo: DormitoryBuildingRepository,
        room_repo: DormitoryRoomRepository,
        assignment_repo: DormitoryAssignmentRepository,
    ) -> None:
        self.building_repo = building_repo
        self.room_repo = room_repo
        self.assignment_repo = assignment_repo

    async def create_building(self, data: DormitoryBuildingCreate) -> DormitoryBuilding:
        building = DormitoryBuilding(**data.model_dump())
        self.building_repo.session.add(building)
        await self.building_repo.session.flush()
        await self.building_repo.session.refresh(building)
        return building

    async def list_buildings(self, tenant_id: uuid.UUID) -> list[DormitoryBuilding]:
        return await self.building_repo.list_by_tenant(tenant_id)

    async def create_room(self, data: DormitoryRoomCreate) -> DormitoryRoom:
        room = DormitoryRoom(**data.model_dump())
        self.room_repo.session.add(room)
        await self.room_repo.session.flush()
        await self.room_repo.session.refresh(room)
        return room

    async def list_rooms(
        self,
        tenant_id: uuid.UUID,
        building_id: uuid.UUID | None = None,
    ) -> list[DormitoryRoom]:
        if building_id is not None:
            return await self.room_repo.list_by_building(building_id, tenant_id)
        return await self.room_repo.list(filters={"tenant_id": tenant_id})

    async def assign_student(self, data: DormitoryAssignmentCreate) -> DormitoryAssignment:
        """Assign a student to a room, vacating any existing active assignment."""
        existing = await self.assignment_repo.get_active_by_student(
            data.student_id, data.tenant_id
        )
        if existing is not None:
            raise ConflictError("Student already has an active dormitory assignment.")

        room = await self.room_repo.get_by_tenant(data.room_id, data.tenant_id)
        if room is None:
            raise NotFoundError("Dormitory room not found.")
        if room.current_occupancy >= room.capacity:
            raise ValidationError("Room is at full capacity.")

        assignment = DormitoryAssignment(**data.model_dump())
        self.assignment_repo.session.add(assignment)

        room.current_occupancy += 1
        if room.current_occupancy >= room.capacity:
            room.status = DormitoryRoomStatus.OCCUPIED
        self.room_repo.session.add(room)

        await self.assignment_repo.session.flush()
        await self.assignment_repo.session.refresh(assignment)
        return assignment

    async def vacate_student(self, student_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        assignment = await self.assignment_repo.get_active_by_student(student_id, tenant_id)
        if assignment is None:
            return False

        assignment.is_active = False
        assignment.vacated_date = date.today()
        self.assignment_repo.session.add(assignment)

        room = await self.room_repo.get(assignment.room_id)
        if room is not None and room.current_occupancy > 0:
            room.current_occupancy -= 1
            if room.status == DormitoryRoomStatus.OCCUPIED:
                room.status = DormitoryRoomStatus.AVAILABLE
            self.room_repo.session.add(room)

        await self.assignment_repo.session.flush()
        return True
