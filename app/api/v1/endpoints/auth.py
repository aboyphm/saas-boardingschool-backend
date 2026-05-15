from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import get_current_active_user
from app.core.database import AsyncSession, get_db
from app.domains.auth.repository import AuthRepository
from app.domains.auth.schemas import (
    AccessTokenResponse,
    ForgotPasswordRequest,
    LogoutRequest,
    OtpResponse,
    RefreshTokenRequest,
    RegisterRequest,
    RequestOtpRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyOtpRequest,
)
from app.domains.auth.service import AuthService
from app.domains.tenants.repository import TenantRepository
from app.domains.users.models import User
from app.domains.users.repository import UserRepository
from app.domains.users.schemas import ChangePasswordRequest, UserResponse

router = APIRouter()


def _get_auth_service(db: AsyncSession) -> AuthService:
    return AuthService(
        user_repo=UserRepository(db),
        auth_repo=AuthRepository(db),
        tenant_repo=TenantRepository(db),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Authenticate with email and password and receive JWT tokens."""
    from app.domains.auth.schemas import LoginRequest
    service = _get_auth_service(db)
    client_ip = request.client.host if request.client else None
    login_data = LoginRequest(email=form_data.username, password=form_data.password)
    return await service.login(login_data, ip_address=client_ip)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccessTokenResponse:
    """Exchange a valid refresh token for a new access token."""
    service = _get_auth_service(db)
    access_token = await service.refresh(data.refresh_token)
    return AccessTokenResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_200_OK, response_class=Response)
async def logout(
    data: LogoutRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Revoke the provided refresh token."""
    service = _get_auth_service(db)
    await service.logout(data.refresh_token)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Self-service registration that creates a new tenant and its first admin account.
    """
    service = _get_auth_service(db)
    return await service.register(data)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.post("/change-password", status_code=status.HTTP_200_OK, response_class=Response)
async def change_password(
    data: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Change the current user's password."""
    from app.domains.users.service import UserService
    service = UserService(UserRepository(db))
    await service.change_password(current_user.id, data)


@router.post("/forgot-password", status_code=status.HTTP_200_OK, response_class=Response)
async def forgot_password(
    data: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Initiate the password-reset flow by email."""
    service = _get_auth_service(db)
    await service.forgot_password(data.email)


@router.post("/reset-password", status_code=status.HTTP_200_OK, response_class=Response)
async def reset_password(
    data: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Consume a password-reset token and set a new password."""
    service = _get_auth_service(db)
    await service.reset_password(data)


@router.post("/request-otp", response_model=OtpResponse)
async def request_otp(
    data: RequestOtpRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OtpResponse:
    """Send a 6-digit OTP to the given WhatsApp number."""
    service = _get_auth_service(db)
    return await service.request_otp(data)


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(
    data: VerifyOtpRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Verify the OTP and issue JWT tokens on success."""
    service = _get_auth_service(db)
    return await service.verify_otp(data)
