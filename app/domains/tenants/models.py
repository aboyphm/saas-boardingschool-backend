from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel, TimestampMixin
from app.shared.enums import SchoolType, SubscriptionPlan, TenantStatus


class Tenant(BaseModel):
    """
    Represents a single school/institution (tenant) on the platform.

    Each tenant receives an isolated data partition enforced via ``tenant_id``
    foreign keys on all domain tables.
    """

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    subdomain: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    custom_domain: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)

    status: Mapped[TenantStatus] = mapped_column(
        String(20), nullable=False, default=TenantStatus.TRIAL, index=True
    )
    plan: Mapped[SubscriptionPlan] = mapped_column(
        String(20), nullable=False, default=SubscriptionPlan.FREE
    )
    school_type: Mapped[SchoolType] = mapped_column(
        String(20), nullable=False, default=SchoolType.BOARDING, server_default="boarding"
    )

    # ─── Branding ─────────────────────────────────────────────────────────────
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    favicon_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_color: Mapped[str] = mapped_column(String(10), default="#1E40AF")
    secondary_color: Mapped[str] = mapped_column(String(10), default="#64748B")
    font_family: Mapped[str] = mapped_column(String(100), default="Inter")

    # ─── Contact ──────────────────────────────────────────────────────────────
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="Indonesia")
    timezone: Mapped[str] = mapped_column(String(60), default="Asia/Jakarta")

    # ─── Quotas ───────────────────────────────────────────────────────────────
    max_students: Mapped[int] = mapped_column(Integer, default=500)
    max_teachers: Mapped[int] = mapped_column(Integer, default=50)
    max_storage_gb: Mapped[int] = mapped_column(Integer, default=10)
    storage_used_gb: Mapped[float] = mapped_column(Float, default=0.0)

    # ─── Subscription lifecycle ───────────────────────────────────────────────
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    subscription_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ─── Arbitrary tenant settings ────────────────────────────────────────────
    settings: Mapped[dict] = mapped_column(JSON, default=dict)

    # ─── Relationships ────────────────────────────────────────────────────────
    branding: Mapped["TenantBranding | None"] = relationship(
        "TenantBranding", back_populates="tenant", uselist=False, lazy="select"
    )


class TenantBranding(BaseModel, TimestampMixin):
    """Extended white-label branding configuration for a tenant."""

    __tablename__ = "tenant_brandings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    login_page_config: Mapped[dict] = mapped_column(JSON, default=dict)
    dashboard_layout: Mapped[dict] = mapped_column(JSON, default=dict)
    email_template: Mapped[dict] = mapped_column(JSON, default=dict)
    pdf_header_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_footer_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    whatsapp_sender_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ─── Relationships ────────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="branding")
