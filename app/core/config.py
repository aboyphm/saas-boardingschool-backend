from __future__ import annotations

import json
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ─── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "Boarding School SaaS"
    VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ─── Security ─────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://saas_user:saas_password@localhost:5432/saas_boardingschool"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 0

    # ─── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://:redis_password@localhost:6379/0"

    # ─── Celery ───────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://:redis_password@localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://:redis_password@localhost:6379/2"

    # ─── CORS & Hosts ─────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]

    # ─── URLs ─────────────────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"

    # ─── Email / SMTP ─────────────────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # ─── WhatsApp ─────────────────────────────────────────────────────────────
    WHATSAPP_API_URL: str = ""
    WHATSAPP_API_TOKEN: str = ""

    # ─── WA OTP Service ───────────────────────────────────────────────────────
    WA_OTP_URL: str = "http://localhost:3100"
    WA_OTP_SECRET: str = "change-me-in-production"

    # ─── AWS S3 ───────────────────────────────────────────────────────────────
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = ""

    # ─── Cloudflare R2 ────────────────────────────────────────────────────────
    CLOUDFLARE_R2_ENDPOINT: str = ""

    # ─── Payment Gateways ─────────────────────────────────────────────────────
    MIDTRANS_SERVER_KEY: str = ""
    MIDTRANS_CLIENT_KEY: str = ""
    XENDIT_SECRET_KEY: str = ""

    # ─── Monitoring ───────────────────────────────────────────────────────────
    SENTRY_DSN: str = ""

    @field_validator("CORS_ORIGINS", "ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_list_from_string(cls, value: str | list[str]) -> list[str]:
        """Accept JSON array strings or native lists from environment variables."""
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
            # Fall back to comma-separated string
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton of application settings."""
    return Settings()
