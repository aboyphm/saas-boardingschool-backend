from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.auth.models import OtpSession, PasswordResetToken


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_reset_token(self, data: dict) -> PasswordResetToken:
        token = PasswordResetToken(**data)
        self.session.add(token)
        await self.session.flush()
        await self.session.refresh(token)
        return token

    async def get_valid_reset_token(self, token_hash: str) -> PasswordResetToken | None:
        stmt = (
            select(PasswordResetToken)
            .where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.is_used.is_(False),
                PasswordResetToken.expires_at > datetime.now(UTC),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_token_used(self, token: PasswordResetToken) -> None:
        token.is_used = True
        self.session.add(token)
        await self.session.flush()

    # ─── OTP methods ──────────────────────────────────────────────────────────

    async def create_otp(self, data: dict) -> OtpSession:
        otp = OtpSession(**data)
        self.session.add(otp)
        await self.session.flush()
        await self.session.refresh(otp)
        return otp

    async def get_valid_otp(self, phone: str, otp_code: str, purpose: str = "login") -> OtpSession | None:
        stmt = (
            select(OtpSession)
            .where(
                OtpSession.phone == phone,
                OtpSession.otp_code == otp_code,
                OtpSession.purpose == purpose,
                OtpSession.is_used.is_(False),
                OtpSession.expires_at > datetime.now(UTC),
            )
            .order_by(OtpSession.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_otp_used(self, otp: OtpSession) -> None:
        otp.is_used = True
        self.session.add(otp)
        await self.session.flush()

    async def invalidate_previous_otps(self, phone: str, purpose: str = "login") -> None:
        stmt = (
            update(OtpSession)
            .where(
                OtpSession.phone == phone,
                OtpSession.purpose == purpose,
                OtpSession.is_used.is_(False),
            )
            .values(is_used=True)
        )
        await self.session.execute(stmt)
