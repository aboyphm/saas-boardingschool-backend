from __future__ import annotations

import uuid
from datetime import date, datetime

from app.shared.base_schema import BaseSchema
from app.shared.enums import AdmissionBatchStatus, AdmissionStatus


class AdmissionBatchCreate(BaseSchema):
    name: str
    description: str | None = None
    open_date: date
    close_date: date
    quota: int = 0
    status: AdmissionBatchStatus = AdmissionBatchStatus.OPEN
    is_active: bool = True


class AdmissionBatchUpdate(BaseSchema):
    name: str | None = None
    description: str | None = None
    open_date: date | None = None
    close_date: date | None = None
    quota: int | None = None
    status: AdmissionBatchStatus | None = None
    is_active: bool | None = None


class AdmissionBatchResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    open_date: date
    close_date: date
    quota: int
    status: AdmissionBatchStatus
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AdmissionCreate(BaseSchema):
    batch_id: uuid.UUID
    applicant_name: str
    parent_name: str | None = None
    phone: str | None = None
    email: str | None = None
    birth_date: date | None = None
    origin_school: str | None = None
    notes: str | None = None


class ReviewRequest(BaseSchema):
    status: AdmissionStatus
    rejection_reason: str | None = None


class AdmissionResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    batch_id: uuid.UUID
    applicant_name: str
    parent_name: str | None
    phone: str | None
    email: str | None
    birth_date: date | None
    origin_school: str | None
    notes: str | None
    status: AdmissionStatus
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime


class AdmissionStatsResponse(BaseSchema):
    total: int
    submitted: int
    under_review: int
    accepted: int
    rejected: int
