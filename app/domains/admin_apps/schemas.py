from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr


class AdminAppsUserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str


class AdminAppsTenantAssign(BaseModel):
    tenant_id: uuid.UUID


class TenantBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: uuid.UUID
    name: str
    subdomain: str


class AdminAppsUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    full_name: str
    email: str
    assigned_tenants: list[TenantBrief]
