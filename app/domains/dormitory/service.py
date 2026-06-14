from __future__ import annotations

import uuid
from datetime import date

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domains.dormitory.models import (
    DormitoryAssignment,
    DormitoryBuilding,
    DormitoryRoom,
    DormitorySupervisor,
)
from app.domains.dormitory.repository import (
    DormitoryAssignmentRepository,
    DormitoryBuildingRepository,
    DormitoryRoomRepository,
    DormitorySupervisorRepository,
)
from app.domains.dormitory.schemas import (
    DormitoryAssignmentCreate,
    DormitoryBuildingCreate,
    DormitoryBuildingUpdate,
    DormitoryRoomCreate,
    DormitoryRoomUpdate,
    DormitorySupervisorCreate,
)
from app.shared.enums import DormitoryRoomStatus


class DormitoryService:
    def __init__(
        self,
        building_repo: DormitoryBuildingRepository,
        room_repo: DormitoryRoomRepository,
        assignment_repo: DormitoryAssignmentRepository,
        supervisor_repo: DormitorySupervisorRepository,
    ) -> None:
        self.building_repo = building_repo
        self.room_repo = room_repo
        self.assignment_repo = assignment_repo
        self.supervisor_repo = supervisor_repo

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

    # ── Building update / delete ───────────────────────────────────────────
    async def update_building(
        self, building_id: uuid.UUID, data: DormitoryBuildingUpdate, tenant_id: uuid.UUID
    ) -> DormitoryBuilding:
        building = await self.building_repo.get_by_tenant(building_id, tenant_id)
        if building is None:
            raise NotFoundError("Building not found.")
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(building, field, value)
        await self.building_repo.session.flush()
        await self.building_repo.session.refresh(building)
        return building

    async def delete_building(self, building_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        building = await self.building_repo.get_by_tenant(building_id, tenant_id)
        if building is None:
            raise NotFoundError("Building not found.")
        rooms = await self.room_repo.list_by_building(building_id, tenant_id)
        if rooms:
            raise ConflictError("Hapus semua kamar terlebih dahulu sebelum menghapus gedung.")
        await self.building_repo.session.delete(building)
        await self.building_repo.session.flush()

    # ── Room update / delete ───────────────────────────────────────────────
    async def update_room(
        self, room_id: uuid.UUID, data: DormitoryRoomUpdate, tenant_id: uuid.UUID
    ) -> DormitoryRoom:
        room = await self.room_repo.get_by_tenant(room_id, tenant_id)
        if room is None:
            raise NotFoundError("Room not found.")
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(room, field, value)
        await self.room_repo.session.flush()
        await self.room_repo.session.refresh(room)
        return room

    async def delete_room(self, room_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        room = await self.room_repo.get_by_tenant(room_id, tenant_id)
        if room is None:
            raise NotFoundError("Room not found.")
        if room.current_occupancy > 0:
            raise ConflictError("Kamar masih berpenghuni. Pindahkan santri terlebih dahulu.")
        await self.room_repo.session.delete(room)
        await self.room_repo.session.flush()

    # ── Assignment queries ─────────────────────────────────────────────────
    async def get_student_assignment(
        self, student_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> DormitoryAssignment | None:
        return await self.assignment_repo.get_active_by_student(student_id, tenant_id)

    async def list_room_assignments(
        self, room_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> list[DormitoryAssignment]:
        return await self.assignment_repo.list_by_room(room_id, tenant_id)

    # ── Supervisor ────────────────────────────────────────────────────────
    async def assign_supervisor(
        self, data: DormitorySupervisorCreate, tenant_id: uuid.UUID
    ) -> DormitorySupervisor:
        existing = await self.supervisor_repo.get_by_teacher_building(
            data.teacher_id, data.building_id, tenant_id
        )
        if existing:
            raise ConflictError("Guru ini sudah menjadi pengawas gedung tersebut.")
        supervisor = DormitorySupervisor(
            tenant_id=tenant_id,
            teacher_id=data.teacher_id,
            building_id=data.building_id,
            assigned_date=data.assigned_date,
        )
        self.supervisor_repo.session.add(supervisor)
        await self.supervisor_repo.session.flush()
        await self.supervisor_repo.session.refresh(supervisor)
        return supervisor

    async def list_supervisors(
        self, building_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> list[DormitorySupervisor]:
        return await self.supervisor_repo.list_by_building(building_id, tenant_id)
