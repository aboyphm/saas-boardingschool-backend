from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import Response as _Response
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import get_logger, setup_logging
from app.core.middleware import RequestLoggingMiddleware, TenantMiddleware

settings = get_settings()
setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application startup and shutdown lifecycle manager.

    Startup:
    - Verify database connectivity.
    - Verify Redis connectivity.

    Shutdown:
    - Close the Redis connection pool.
    """
    setup_logging(settings.LOG_LEVEL)

    # ─── Startup ──────────────────────────────────────────────────────────────
    logger.info("Starting application", environment=settings.ENVIRONMENT)

    # Verify database connection
    try:
        from sqlalchemy import text
        from app.core.database import async_engine
        async with async_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception as exc:
        logger.error("Database connection failed", error=str(exc))
        raise

    # Verify Redis connection
    try:
        from app.core.redis import get_redis_pool
        redis = await get_redis_pool()
        await redis.ping()
        logger.info("Redis connection verified")
    except Exception as exc:
        logger.warning("Redis connection failed — continuing without cache", error=str(exc))

    # Load CORS origins from DB into the in-memory registry
    from app.core.cors_registry import set_origins
    from app.core.database import AsyncSessionLocal
    from app.domains.cors.repository import CorsOriginRepository

    static_origins = set(settings.CORS_ORIGINS)
    db_origins: set[str] = set()
    try:
        async with AsyncSessionLocal() as _cors_session:
            _repo = CorsOriginRepository(_cors_session)
            entries = await _repo.list_active()
            db_origins = {e.origin for e in entries}
    except Exception as exc:
        logger.warning("Could not load CORS origins from DB at startup", error=str(exc))

    merged = static_origins | db_origins
    set_origins(merged)
    logger.info(
        "CORS registry loaded",
        total=len(merged),
        from_env=len(static_origins),
        from_db=len(db_origins),
    )

    # Initialise Sentry in non-development environments
    if settings.SENTRY_DSN and not settings.is_development:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)
        logger.info("Sentry initialised")

    yield

    # ─── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Shutting down application")

    try:
        from app.core.redis import close_redis_pool
        await close_redis_pool()
        logger.info("Redis connection pool closed")
    except Exception as exc:
        logger.warning("Error closing Redis pool", error=str(exc))

    try:
        from app.core.database import async_engine
        await async_engine.dispose()
        logger.info("Database engine disposed")
    except Exception as exc:
        logger.warning("Error disposing database engine", error=str(exc))


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title="Boarding School SaaS API",
        version="1.0.0",
        description=(
            "Enterprise multi-tenant SaaS platform for multi-type boarding school and educational institution "
            "management. Supports students, teachers, attendance, "
            "finance, dormitory management, and more."
        ),
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
        redirect_slashes=False,
    )

    # ─── Middleware (applied in reverse order) ────────────────────────────────
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(TenantMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    if settings.ALLOWED_HOSTS:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS,
        )

    # ─── Dynamic CORS middleware (DB-managed origins) ─────────────────────────
    from app.core.cors_registry import get_allowed

    @app.middleware("http")
    async def _dynamic_cors(request: Request, call_next):
        origin = request.headers.get("origin", "")
        allowed = get_allowed()

        # Preflight
        if request.method == "OPTIONS" and origin:
            if origin in allowed:
                return _Response(
                    status_code=200,
                    headers={
                        "Access-Control-Allow-Origin": origin,
                        "Access-Control-Allow-Credentials": "true",
                        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                        "Access-Control-Allow-Headers": "*",
                        "Access-Control-Max-Age": "600",
                        "Vary": "Origin",
                    },
                )
            return _Response(status_code=403)

        response = await call_next(request)

        if origin and origin in allowed:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Vary"] = "Origin"

        return response

    # ─── Exception handlers ───────────────────────────────────────────────────
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred.",
                    "details": {},
                }
            },
        )

    # ─── Routes ───────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix="/api/v1")

    from app.api.v1.websocket.exam_monitor import ws_router as exam_ws_router
    app.include_router(exam_ws_router)

    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def health_check() -> dict:
        return {"status": "ok", "version": "1.0.0"}

    return app


app = create_app()
