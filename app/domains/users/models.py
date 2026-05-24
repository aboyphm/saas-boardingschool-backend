from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel, SoftDeleteMixin, TimestampMixin
from app.shared.enums import UserRole


class User(BaseModel, SoftDeleteMixin):
    """
    Platform user account.

    Super administrators have ``tenant_id=None``. All other roles must
    belong to exactly one tenant.
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", "tenant_id", name="uq_user_email_tenant"),
    )

    # tenant_id is nullable for SUPER_ADMIN accounts
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    dial_code: Mapped[str] = mapped_column(String(5), nullable=False, default="62", server_default="62")
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    role: Mapped[UserRole] = mapped_column(String(30), nullable=False, index=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ─── Credentials ──────────────────────────────────────────────────────────
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ─── Relationships ────────────────────────────────────────────────────────
    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )


class RolePermission(BaseModel):
    """RBAC role definition with a JSON array of permission strings."""

    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    permissions: Mapped[list] = mapped_column(JSON, default=list)


class UserSession(BaseModel, TimestampMixin):
    """Tracks active refresh token sessions per user and device."""

    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Store only the hash of the refresh token, never the raw value.
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    device_info: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # ─── Relationships ────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="sessions")


class AdminAppsTenant(BaseModel):
    """Maps which tenants an ADMIN_APPS user is allowed to access."""

    __tablename__ = "admin_apps_tenants"
    __table_args__ = (
        UniqueConstraint("admin_apps_user_id", "tenant_id", name="uq_admin_apps_user_tenant"),
    )

    admin_apps_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
