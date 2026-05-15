from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Resolve the current tenant from the incoming request.

    Extraction order (first match wins):
    1. ``X-Tenant-ID`` header (UUID string) — useful for API clients.
    2. Subdomain of the ``Host`` header, e.g. ``school1.platform.com``.

    The resolved value is stored on ``request.state.tenant_slug`` (str) or
    ``request.state.tenant_id`` (str | None).  Downstream code is responsible
    for looking up the tenant record from the database.
    """

    # Subdomains that do not correspond to individual tenants.
    _SYSTEM_SUBDOMAINS: frozenset[str] = frozenset({"www", "api", "admin", "app", "static"})

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Prefer explicit header (useful in development and for mobile apps).
        explicit_tenant_id = request.headers.get("X-Tenant-ID")
        if explicit_tenant_id:
            request.state.tenant_id = explicit_tenant_id
            request.state.tenant_slug = None
        else:
            # Derive tenant from the subdomain.
            host = request.headers.get("host", "").split(":")[0]  # Strip port
            parts = host.split(".")
            if len(parts) >= 3 and parts[0] not in self._SYSTEM_SUBDOMAINS:
                request.state.tenant_slug = parts[0]
                request.state.tenant_id = None
            else:
                request.state.tenant_slug = None
                request.state.tenant_id = None

        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log every HTTP request with method, path, status code, and duration.

    Sensitive paths (login, token refresh) are logged at DEBUG level to
    avoid leaking credentials in production logs.
    """

    _SENSITIVE_PATHS: frozenset[str] = frozenset({
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/reset-password",
        "/api/v1/auth/change-password",
    })

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        path = request.url.path
        is_sensitive = path in self._SENSITIVE_PATHS

        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client_ip": request.client.host if request.client else "unknown",
        }

        if is_sensitive:
            logger.debug("HTTP request", extra=log_data)
        elif response.status_code >= 500:
            logger.error("HTTP request failed", extra=log_data)
        elif response.status_code >= 400:
            logger.warning("HTTP request client error", extra=log_data)
        else:
            logger.info("HTTP request", extra=log_data)

        # Propagate the request ID to the caller for distributed tracing.
        response.headers["X-Request-ID"] = request_id
        return response
