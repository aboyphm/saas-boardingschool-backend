from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_active_user, require_roles
from app.core.database import AsyncSession, get_db
from app.domains.dormitory.repository import (
    DormitoryAssignmentRepository,
    DormitoryBuildingRepository,
    DormitoryRoomRepository,
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
)
from app.domains.dormitory.service import DormitoryService
from app.domains.users.models import User
from app.shared.enums import UserRole

router = APIRouter()


def _get_service(db: AsyncSession) -> DormitoryService:
    return DormitoryService(
        building_repo=DormitoryBuildingRepository(db),
        room_repo=DormitoryRoomRepository(db),
        assignment_repo=DormitoryAssignmentRepository(db),
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
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.BOARDING_SUPERVISOR, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DormitoryBuildingResponse:
    service = _get_service(db)
    building = await service.create_building(data)
    return DormitoryBuildingResponse.model_validate(building)


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
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.BOARDING_SUPERVISOR, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DormitoryRoomResponse:
    service = _get_service(db)
    room = await service.create_room(data)
    return DormitoryRoomResponse.model_validate(room)


@router.post("/assignments", response_model=DormitoryAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def assign_student(
    data: DormitoryAssignmentCreate,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.BOARDING_SUPERVISOR, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DormitoryAssignmentResponse:
    service = _get_service(db)
    assignment = await service.assign_student(data)
    return DormitoryAssignmentResponse.model_validate(assignment)


@router.delete("/assignments/{student_id}", status_code=status.HTTP_200_OK)
async def vacate_student(
    student_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_roles(
        UserRole.TENANT_ADMIN, UserRole.BOARDING_SUPERVISOR, UserRole.SUPER_ADMIN
    ))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    service = _get_service(db)
    await service.vacate_student(student_id, current_user.tenant_id)
