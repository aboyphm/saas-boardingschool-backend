from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_active_user, require_roles
from app.core.database import AsyncSession, get_db
from app.core.exceptions import ForbiddenError
from app.domains.dormitory.repository import (
    DormitoryAssignmentRepository,
    DormitoryBuildingRepository,
    DormitoryRoomRepository,
    DormitorySupervisorRepository,
)
from app.domains.dormitory.schemas import (
    DormitoryAssignmentCreate,
    DormitoryAssignmentResponse,
    DormitoryBuildingCreate,
    DormitoryBuildingResponse,
    DormitoryBuildingUpdate,
    DormitoryRoomCreate,
    DormitoryRoomResponse,
    DormitoryRoomUpdate,
    DormitorySupervisorCreate,
    DormitorySupervisorResponse,
)
from app.domains.dormitory.service import DormitoryService
from app.domains.users.models import User
from app.shared.enums import UserRole

router = APIRouter()

WRITE_ROLES = (UserRole.TENANT_ADMIN, UserRole.BOARDING_SUPERVISOR, UserRole.SUPER_ADMIN)


def _tid(user: User) -> uuid.UUID:
    if user.tenant_id is None:
        raise ForbiddenError("A tenant context is required.")
    return user.tenant_id


def _get_service(db: AsyncSession) -> DormitoryService:
    return DormitoryService(
        building_repo=DormitoryBuildingRepository(db),
        room_repo=DormitoryRoomRepository(db),
        assignment_repo=DormitoryAssignmentRepository(db),
        supervisor_repo=DormitorySupervisorRepository(db),
    )


@router.get("/buildings", response_model=list[DormitoryBuildingResponse])
async def list_buildings(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DormitoryBuildingResponse]:
    service = _get_service(db)
    buildings = await service.list_buildings(current_user.tenant_id)
    return [DormitoryBuildingResponse.model_validate(b) for b in buildings]


@router.post("/buildings", response_model=DormitoryBuildingResponse, status_code=status.HTTP_201_CREATED)
async def create_building(
    data: DormitoryBuildingCreate,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DormitoryBuildingResponse:
    service = _get_service(db)
    building = await service.create_building(data)
    return DormitoryBuildingResponse.model_validate(building)


@router.put("/buildings/{building_id}", response_model=DormitoryBuildingResponse)
async def update_building(
    building_id: uuid.UUID,
    data: DormitoryBuildingUpdate,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DormitoryBuildingResponse:
    service = _get_service(db)
    building = await service.update_building(building_id, data, _tid(current_user))
    return DormitoryBuildingResponse.model_validate(building)


@router.delete("/buildings/{building_id}", status_code=status.HTTP_200_OK)
async def delete_building(
    building_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _get_service(db)
    await service.delete_building(building_id, _tid(current_user))
    return {"ok": True}


@router.get("/buildings/{building_id}/supervisors", response_model=list[DormitorySupervisorResponse])
async def list_supervisors(
    building_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DormitorySupervisorResponse]:
    service = _get_service(db)
    supervisors = await service.list_supervisors(building_id, _tid(current_user))
    return [DormitorySupervisorResponse.model_validate(s) for s in supervisors]


@router.post("/buildings/{building_id}/supervisors", response_model=DormitorySupervisorResponse, status_code=status.HTTP_201_CREATED)
async def assign_supervisor(
    building_id: uuid.UUID,
    data: DormitorySupervisorCreate,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DormitorySupervisorResponse:
    # Path parameter is authoritative; override any building_id in the body.
    data = data.model_copy(update={"building_id": building_id})
    service = _get_service(db)
    supervisor = await service.assign_supervisor(data, _tid(current_user))
    return DormitorySupervisorResponse.model_validate(supervisor)


@router.get("/rooms", response_model=list[DormitoryRoomResponse])
async def list_rooms(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    building_id: uuid.UUID | None = Query(default=None),
) -> list[DormitoryRoomResponse]:
    service = _get_service(db)
    rooms = await service.list_rooms(current_user.tenant_id, building_id)
    return [DormitoryRoomResponse.model_validate(r) for r in rooms]


@router.post("/rooms", response_model=DormitoryRoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    data: DormitoryRoomCreate,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DormitoryRoomResponse:
    service = _get_service(db)
    room = await service.create_room(data)
    return DormitoryRoomResponse.model_validate(room)


@router.put("/rooms/{room_id}", response_model=DormitoryRoomResponse)
async def update_room(
    room_id: uuid.UUID,
    data: DormitoryRoomUpdate,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DormitoryRoomResponse:
    service = _get_service(db)
    room = await service.update_room(room_id, data, _tid(current_user))
    return DormitoryRoomResponse.model_validate(room)


@router.delete("/rooms/{room_id}", status_code=status.HTTP_200_OK)
async def delete_room(
    room_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _get_service(db)
    await service.delete_room(room_id, _tid(current_user))
    return {"ok": True}


@router.post("/assignments", response_model=DormitoryAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def assign_student(
    data: DormitoryAssignmentCreate,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DormitoryAssignmentResponse:
    service = _get_service(db)
    assignment = await service.assign_student(data)
    return DormitoryAssignmentResponse.model_validate(assignment)


@router.get("/assignments/student/{student_id}", response_model=DormitoryAssignmentResponse | None)
async def get_student_assignment(
    student_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DormitoryAssignmentResponse | None:
    if current_user.role == UserRole.STUDENT:
        from app.domains.students.repository import StudentRepository
        repo = StudentRepository(db)
        own = await repo.get_by_user_id(current_user.id, _tid(current_user))
        if own is None or own.id != student_id:
            raise ForbiddenError("Students can only view their own assignment.")
    service = _get_service(db)
    assignment = await service.get_student_assignment(student_id, _tid(current_user))
    if assignment is None:
        return None
    return DormitoryAssignmentResponse.model_validate(assignment)


@router.get("/assignments/room/{room_id}", response_model=list[DormitoryAssignmentResponse])
async def list_room_assignments(
    room_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DormitoryAssignmentResponse]:
    service = _get_service(db)
    assignments = await service.list_room_assignments(room_id, _tid(current_user))
    return [DormitoryAssignmentResponse.model_validate(a) for a in assignments]


@router.delete("/assignments/{student_id}", status_code=status.HTTP_200_OK)
async def vacate_student(
    student_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = _get_service(db)
    await service.vacate_student(student_id, current_user.tenant_id)
    return {"ok": True}
