from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, field_validator

from app.shared.base_schema import BaseSchema
from app.shared.enums import UserRole


class UserCreate(BaseSchema):
    email: EmailStr
    full_name: str
    password: str
    role: UserRole = UserRole.ADMIN_STAFF
    tenant_id: uuid.UUID | None = None
    phone: str | None = None
    dial_code: str = "62"
    username: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return value


class UserUpdate(BaseSchema):
    full_name: str | None = None
    phone: str | None = None
    dial_code: str | None = None
    avatar_url: str | None = None
    username: str | None = None
    is_active: bool | None = None


class UserResponse(BaseSchema):
    id: uuid.UUID
    email: str
    full_name: str
    username: str | None
    phone: str | None
    dial_code: str
    avatar_url: str | None
    role: UserRole
    tenant_id: uuid.UUID | None
    is_active: bool
    is_verified: bool
    mfa_enabled: bool
    last_login_at: datetime | None
    created_at: datetime


class ChangePasswordRequest(BaseSchema):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return value
