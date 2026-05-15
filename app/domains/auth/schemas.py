from __future__ import annotations

import uuid

from pydantic import EmailStr, field_validator

from app.shared.base_schema import BaseSchema
from app.domains.users.schemas import UserResponse


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseSchema):
    refresh_token: str


class AccessTokenResponse(BaseSchema):
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseSchema):
    """Self-registration payload. Creates a new tenant and admin user."""
    school_name: str
    subdomain: str
    admin_email: EmailStr
    admin_full_name: str
    admin_password: str
    contact_phone: str | None = None

    @field_validator("admin_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return value

    @field_validator("subdomain")
    @classmethod
    def subdomain_format(cls, value: str) -> str:
        import re
        cleaned = re.sub(r"[^a-z0-9-]", "", value.lower())
        if not cleaned:
            raise ValueError("Subdomain must contain at least one alphanumeric character.")
        return cleaned


class ForgotPasswordRequest(BaseSchema):
    email: EmailStr


class ResetPasswordRequest(BaseSchema):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return value


class LogoutRequest(BaseSchema):
    refresh_token: str


class RequestOtpRequest(BaseSchema):
    phone: str


class VerifyOtpRequest(BaseSchema):
    phone: str
    otp_code: str


class OtpResponse(BaseSchema):
    message: str
