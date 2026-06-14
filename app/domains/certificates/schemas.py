from __future__ import annotations

import uuid
from datetime import date, datetime

from app.shared.base_schema import BaseSchema
from app.shared.enums import CertificateType


class CertificateCreate(BaseSchema):
    student_id: uuid.UUID
    certificate_type: CertificateType
    title: str
    description: str | None = None
    issued_at: date


class CertificateUpdate(BaseSchema):
    title: str | None = None
    description: str | None = None


class RevokeRequest(BaseSchema):
    revocation_reason: str | None = None


class CertificateResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    student_id: uuid.UUID
    issued_by: uuid.UUID | None
    certificate_number: str
    certificate_type: CertificateType
    title: str
    description: str | None
    issued_at: date
    is_revoked: bool
    revoked_at: datetime | None
    revoked_by: uuid.UUID | None
    revocation_reason: str | None
    created_at: datetime
    updated_at: datetime
