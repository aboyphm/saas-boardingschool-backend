from __future__ import annotations

import hashlib
import random
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import httpx

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.domains.auth.repository import AuthRepository
from app.domains.auth.schemas import (
    LoginRequest,
    OtpResponse,
    RegisterRequest,
    RequestOtpRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyOtpRequest,
)
from app.domains.tenants.models import Tenant
from app.domains.tenants.repository import TenantRepository
from app.domains.tenants.schemas import TenantCreate
from app.domains.users.models import User
from app.domains.users.repository import UserRepository
from app.domains.users.schemas import UserCreate
from app.shared.enums import TenantStatus, UserRole


def _hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of a token string."""
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        auth_repo: AuthRepository,
        tenant_repo: TenantRepository,
    ) -> None:
        self.user_repo = user_repo
        self.auth_repo = auth_repo
        self.tenant_repo = tenant_repo

    def _build_token_payload(self, user: User) -> dict:
        return {
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "role": user.role,
        }

    async def login(self, data: LoginRequest, ip_address: str | None = None) -> TokenResponse:
        """Authenticate a user and issue JWT access + refresh tokens."""
        user = await self.user_repo.get_by_email(data.email)
        if user is None or not verify_password(data.password, user.password_hash):
            raise UnauthorizedError("Invalid email or password.")

        if not user.is_active:
            raise UnauthorizedError("This account has been deactivated.")

        payload = self._build_token_payload(user)
        access_token = create_access_token(payload)
        refresh_token = create_refresh_token(payload)

        token_hash = _hash_token(refresh_token)
        expires_at = datetime.now(UTC) + timedelta(days=7)

        await self.user_repo.create_session({
            "user_id": user.id,
            "refresh_token_hash": token_hash,
            "ip_address": ip_address,
            "expires_at": expires_at,
            "device_info": {},
        })

        # Update last login timestamp
        user.last_login_at = datetime.now(UTC)
        self.user_repo.session.add(user)
        await self.user_repo.session.flush()
        await self.user_repo.session.refresh(user)

        from app.domains.users.schemas import UserResponse
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )

    async def refresh(self, refresh_token: str) -> str:
        """Issue a new access token from a valid refresh token."""
        payload = verify_token(refresh_token)
        if payload.token_type != "refresh":
            raise UnauthorizedError("Invalid token type.")

        token_hash = _hash_token(refresh_token)
        session = await self.user_repo.get_session_by_token_hash(token_hash)
        if session is None:
            raise UnauthorizedError("Refresh token has been revoked or does not exist.")

        if session.expires_at < datetime.now(UTC):
            raise UnauthorizedError("Refresh token has expired.")

        user = await self.user_repo.get(payload.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("User account is inactive.")

        return create_access_token(self._build_token_payload(user))

    async def logout(self, refresh_token: str) -> None:
        """Revoke the provided refresh token session."""
        token_hash = _hash_token(refresh_token)
        session = await self.user_repo.get_session_by_token_hash(token_hash)
        if session is not None:
            await self.user_repo.revoke_session(session.id)

    async def register(self, data: RegisterRequest) -> TokenResponse:
        """
        Self-registration flow: create a tenant and its first admin user.
        """
        slug = data.subdomain

        tenant_data = TenantCreate(
            name=data.school_name,
            slug=slug,
            subdomain=data.subdomain,
            contact_email=data.admin_email,
            contact_phone=data.contact_phone,
        )
        tenant = await self.tenant_repo.create(tenant_data)

        user_data = UserCreate(
            email=data.admin_email,
            full_name=data.admin_full_name,
            password=data.admin_password,
            role=UserRole.TENANT_ADMIN,
            tenant_id=tenant.id,
        )

        from app.core.security import get_password_hash as hash_pw
        hashed = hash_pw(user_data.password)
        user_dict = user_data.model_dump(exclude={"password"})
        user_dict["password_hash"] = hashed
        user = User(**user_dict)
        self.user_repo.session.add(user)
        await self.user_repo.session.flush()
        await self.user_repo.session.refresh(user)

        payload = self._build_token_payload(user)
        access_token = create_access_token(payload)
        refresh_token = create_refresh_token(payload)

        token_hash = _hash_token(refresh_token)
        await self.user_repo.create_session({
            "user_id": user.id,
            "refresh_token_hash": token_hash,
            "ip_address": None,
            "expires_at": datetime.now(UTC) + timedelta(days=7),
            "device_info": {},
        })

        from app.domains.users.schemas import UserResponse
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )

    async def forgot_password(self, email: str) -> None:
        """Generate a password-reset token and (in production) queue an email."""
        user = await self.user_repo.get_by_email(email)
        if user is None:
            # Do not reveal whether the email exists.
            return

        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)

        await self.auth_repo.create_reset_token({
            "user_id": user.id,
            "token_hash": token_hash,
            "expires_at": datetime.now(UTC) + timedelta(hours=1),
        })

        # TODO: Enqueue send_email_notification task here.

    async def reset_password(self, data: ResetPasswordRequest) -> None:
        """Consume a reset token and update the user's password."""
        token_hash = _hash_token(data.token)
        reset_token = await self.auth_repo.get_valid_reset_token(token_hash)
        if reset_token is None:
            raise UnauthorizedError("Invalid or expired password-reset token.")

        user = await self.user_repo.get(reset_token.user_id)
        if user is None:
            raise NotFoundError("User not found.")

        user.password_hash = get_password_hash(data.new_password)
        self.user_repo.session.add(user)
        await self.auth_repo.mark_token_used(reset_token)

        # Revoke all active sessions for security.
        await self.user_repo.revoke_all_sessions(user.id)

    async def request_otp(self, data: RequestOtpRequest) -> OtpResponse:
        """Generate a 6-digit OTP and deliver it via the WA OTP microservice."""
        settings = get_settings()

        # Normalize phone: strip spaces/dashes/+, ensure 628x format (08x → 628x, 8x → 628x)
        phone = data.phone.strip().replace(" ", "").replace("-", "").lstrip("+")
        if phone.startswith("0"):
            phone = "62" + phone[1:]
        elif not phone.startswith("62"):
            phone = "62" + phone

        user = await self.user_repo.get_by_phone(phone)
        if user is None:
            # Respond ambiguously — don't reveal whether the number is registered
            return OtpResponse(message="If this number is registered, an OTP has been sent.")

        if not user.is_active and user.is_verified:
            raise UnauthorizedError("This account has been deactivated.")

        otp_code = f"{random.randint(0, 999999):06d}"
        expires_at = datetime.now(UTC) + timedelta(minutes=5)

        # Invalidate any pending OTPs for this phone before creating a new one
        await self.auth_repo.invalidate_previous_otps(phone)
        await self.auth_repo.create_otp({
            "tenant_id": user.tenant_id,
            "user_id": user.id,
            "phone": phone,
            "otp_code": otp_code,
            "purpose": "login",
            "expires_at": expires_at,
        })

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.WA_OTP_URL}/send-otp",
                json={"phone": phone, "otp_code": otp_code, "appName": "Academizy"},
                headers={"X-Internal-Secret": settings.WA_OTP_SECRET},
            )
            resp.raise_for_status()

        return OtpResponse(message="OTP has been sent to your WhatsApp number.")

    async def verify_otp(self, data: VerifyOtpRequest) -> TokenResponse:
        """Verify the submitted OTP and issue JWT tokens on success."""
        phone = data.phone.strip().replace(" ", "").replace("-", "").lstrip("+")
        if phone.startswith("0"):
            phone = "62" + phone[1:]
        elif not phone.startswith("62"):
            phone = "62" + phone

        otp_session = await self.auth_repo.get_valid_otp(phone, data.otp_code)
        if otp_session is None:
            raise UnauthorizedError("Invalid or expired OTP.")

        if otp_session.user_id is None:
            raise UnauthorizedError("Invalid OTP session.")
        user = await self.user_repo.get(otp_session.user_id)
        if user is None:
            raise UnauthorizedError("User account not found.")
        if not user.is_active and user.is_verified:
            raise UnauthorizedError("User account is inactive.")

        await self.auth_repo.mark_otp_used(otp_session)

        if not user.is_verified:
            user.is_active = True
            user.is_verified = True

        payload = self._build_token_payload(user)
        access_token = create_access_token(payload)
        refresh_token = create_refresh_token(payload)

        token_hash = _hash_token(refresh_token)
        await self.user_repo.create_session({
            "user_id": user.id,
            "refresh_token_hash": token_hash,
            "ip_address": None,
            "expires_at": datetime.now(UTC) + timedelta(days=7),
            "device_info": {},
        })

        user.last_login_at = datetime.now(UTC)
        self.user_repo.session.add(user)
        await self.user_repo.session.flush()
        await self.user_repo.session.refresh(user)

        from app.domains.users.schemas import UserResponse
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )
