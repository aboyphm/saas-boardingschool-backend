from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError

settings = get_settings()

# ─── Password hashing ─────────────────────────────────────────────────────────
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """Return the bcrypt hash of a plain-text password."""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against its stored hash."""
    return _pwd_context.verify(plain_password, hashed_password)


# ─── Token payload ────────────────────────────────────────────────────────────
class TokenPayload:
    """Parsed JWT payload extracted from a valid access or refresh token."""

    def __init__(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID | None,
        role: str,
        token_type: str,
        exp: datetime,
    ) -> None:
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role
        self.token_type = token_type
        self.exp = exp


# ─── Token creation ───────────────────────────────────────────────────────────
def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token.

    :param data: Payload claims (must include ``sub``, ``tenant_id``, ``role``).
    :param expires_delta: Override the default expiry window.
    :returns: Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    """
    Create a signed JWT refresh token with a longer expiry.

    :param data: Payload claims.
    :returns: Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> TokenPayload:
    """
    Decode and validate a JWT token.

    :param token: Raw JWT string.
    :returns: Parsed :class:`TokenPayload`.
    :raises UnauthorizedError: If the token is invalid, expired, or malformed.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError as exc:
        raise UnauthorizedError(message="Invalid or expired token") from exc

    sub: str | None = payload.get("sub")
    if sub is None:
        raise UnauthorizedError(message="Token missing subject claim")

    try:
        user_id = uuid.UUID(sub)
    except ValueError as exc:
        raise UnauthorizedError(message="Token subject is not a valid UUID") from exc

    raw_tenant_id: str | None = payload.get("tenant_id")
    tenant_id: uuid.UUID | None = None
    if raw_tenant_id is not None:
        try:
            tenant_id = uuid.UUID(raw_tenant_id)
        except ValueError as exc:
            raise UnauthorizedError(message="Token tenant_id is not a valid UUID") from exc

    return TokenPayload(
        user_id=user_id,
        tenant_id=tenant_id,
        role=payload.get("role", ""),
        token_type=payload.get("type", "access"),
        exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
    )
