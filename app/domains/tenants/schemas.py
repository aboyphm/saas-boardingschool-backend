from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, field_validator

from app.shared.base_schema import BaseSchema
from app.shared.enums import SubscriptionPlan, TenantStatus


class TenantCreate(BaseSchema):
    name: str
    slug: str
    subdomain: str
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    plan: SubscriptionPlan = SubscriptionPlan.TRIAL if False else SubscriptionPlan.FREE
    country: str = "Indonesia"
    timezone: str = "Asia/Jakarta"

    @field_validator("slug", "subdomain")
    @classmethod
    def must_be_lowercase_slug(cls, value: str) -> str:
        import re
        cleaned = re.sub(r"[^a-z0-9-]", "", value.lower())
        if not cleaned:
            raise ValueError("Must contain at least one alphanumeric character.")
        return cleaned


class TenantUpdate(BaseSchema):
    name: str | None = None
    custom_domain: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    address: str | None = None
    city: str | None = None
    logo_url: str | None = None
    favicon_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    font_family: str | None = None
    timezone: str | None = None
    settings: dict | None = None


class TenantBrandingUpdate(BaseSchema):
    login_page_config: dict | None = None
    dashboard_layout: dict | None = None
    email_template: dict | None = None
    pdf_header_html: str | None = None
    pdf_footer_html: str | None = None
    whatsapp_sender_name: str | None = None


class TenantResponse(BaseSchema):
    id: uuid.UUID
    name: str
    slug: str
    subdomain: str
    custom_domain: str | None
    status: TenantStatus
    plan: SubscriptionPlan
    logo_url: str | None
    primary_color: str
    secondary_color: str
    font_family: str
    contact_email: str | None
    contact_phone: str | None
    city: str | None
    country: str
    timezone: str
    max_students: int
    max_teachers: int
    storage_used_gb: float
    max_storage_gb: int
    trial_ends_at: datetime | None
    subscription_ends_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TenantStatsResponse(BaseSchema):
    tenant_id: uuid.UUID
    total_students: int
    total_teachers: int
    total_active_users: int
    storage_used_gb: float
    storage_limit_gb: int
    outstanding_invoices: int
    total_revenue_month: float
