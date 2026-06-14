from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_active_user, require_roles
from app.core.database import AsyncSession, get_db
from app.core.exceptions import ForbiddenError
from app.domains.certificates.repository import CertificateRepository
from app.domains.certificates.schemas import (
    CertificateCreate, CertificateResponse, CertificateUpdate, RevokeRequest,
)
from app.domains.certificates.service import CertificateService
from app.domains.users.models import User
from app.shared.enums import CertificateType, UserRole

router = APIRouter()

WRITE_ROLES = (UserRole.TENANT_ADMIN, UserRole.ADMIN_STAFF, UserRole.SUPER_ADMIN)


def _tid(user: User) -> uuid.UUID:
    if user.tenant_id is None:
        raise ForbiddenError("A tenant context is required.")
    return user.tenant_id


def _get_service(db: AsyncSession) -> CertificateService:
    return CertificateService(repo=CertificateRepository(db))


@router.get("", response_model=list[CertificateResponse])
async def list_certificates(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    student_id: uuid.UUID | None = Query(default=None),
    certificate_type: CertificateType | None = Query(default=None),
    include_revoked: bool = Query(default=False),
) -> list[CertificateResponse]:
    service = _get_service(db)
    certs = await service.list_certificates(
        _tid(current_user), student_id, certificate_type, include_revoked,
    )
    return [CertificateResponse.model_validate(c) for c in certs]


@router.post("", response_model=CertificateResponse, status_code=status.HTTP_201_CREATED)
async def issue_certificate(
    data: CertificateCreate,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CertificateResponse:
    service = _get_service(db)
    cert = await service.issue_certificate(data, _tid(current_user), current_user.id)
    return CertificateResponse.model_validate(cert)


@router.get("/verify/{certificate_number}", response_model=CertificateResponse | None)
async def verify_certificate(
    certificate_number: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CertificateResponse | None:
    """Public endpoint — no authentication required."""
    service = _get_service(db)
    cert = await service.verify_certificate(certificate_number)
    if cert is None:
        return None
    return CertificateResponse.model_validate(cert)


@router.put("/{cert_id}", response_model=CertificateResponse)
async def update_certificate(
    cert_id: uuid.UUID,
    data: CertificateUpdate,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CertificateResponse:
    service = _get_service(db)
    cert = await service.update_certificate(cert_id, data, _tid(current_user))
    return CertificateResponse.model_validate(cert)


@router.post("/{cert_id}/revoke", response_model=CertificateResponse)
async def revoke_certificate(
    cert_id: uuid.UUID,
    data: RevokeRequest,
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CertificateResponse:
    service = _get_service(db)
    cert = await service.revoke_certificate(
        cert_id, data, current_user.id, _tid(current_user),
    )
    return CertificateResponse.model_validate(cert)
