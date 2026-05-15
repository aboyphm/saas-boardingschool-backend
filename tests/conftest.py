from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.domains.tenants.models import Tenant
from app.domains.users.models import User
from app.main import app
from app.shared.enums import SubscriptionPlan, TenantStatus, UserRole

# ─── Test database ────────────────────────────────────────────────────────────
# Use saas_test if it exists; fall back to saas_boardingschool when the test
# database has not been provisioned yet (e.g. local dev without CREATEDB).
def _saas_test_db_exists() -> bool:
    """Return True if the saas_test database is reachable.

    Uses a raw asyncpg connection in a dedicated OS thread so the probe loop
    never leaks into the pytest-asyncio session loop.
    """
    import asyncio
    import asyncpg  # type: ignore[import]
    import threading

    result: list[bool] = []

    def _run() -> None:
        async def _check() -> bool:
            try:
                conn = await asyncpg.connect(
                    host="localhost", port=5432,
                    user="saas_user", password="saas_password",
                    database="saas_test",
                )
                await conn.close()
                return True
            except Exception:
                return False

        result.append(asyncio.run(_check()))

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join()
    return bool(result and result[0])


_SAAS_TEST_EXISTS = _saas_test_db_exists()
TEST_DATABASE_URL = (
    "postgresql+asyncpg://saas_user:saas_password@localhost:5432/saas_test"
    if _SAAS_TEST_EXISTS
    else "postgresql+asyncpg://saas_user:saas_password@localhost:5432/saas_boardingschool"
)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create a shared event loop for the entire test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


_IS_FALLBACK_DB = TEST_DATABASE_URL.endswith("/saas_boardingschool")


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables before the session and drop them after.

    When falling back to saas_boardingschool (no CREATEDB privilege), skip
    drop_all so we don't destroy the real schema; the per-test rollback in
    db_session is sufficient isolation.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    if not _IS_FALLBACK_DB:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional database session that is rolled back after each test."""
    async with TestSessionLocal() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Yield an async test client with the test DB session injected."""
    from httpx import ASGITransport
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Create and return a test tenant."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Test Pesantren",
        slug="test-pesantren",
        subdomain="test",
        status=TenantStatus.ACTIVE,
        plan=SubscriptionPlan.PROFESSIONAL,
    )
    db_session.add(tenant)
    await db_session.flush()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def test_admin_user(db_session: AsyncSession, test_tenant: Tenant) -> User:
    """Create and return a TENANT_ADMIN user for the test tenant."""
    user = User(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        email="admin@test.com",
        full_name="Test Admin",
        role=UserRole.TENANT_ADMIN,
        is_active=True,
        is_verified=True,
        password_hash=get_password_hash("TestPassword123"),
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_token(test_admin_user: User) -> str:
    """Return a valid JWT access token for the test admin user."""
    from app.core.security import create_access_token
    return create_access_token({
        "sub": str(test_admin_user.id),
        "tenant_id": str(test_admin_user.tenant_id),
        "role": test_admin_user.role.value,
    })


@pytest_asyncio.fixture
async def auth_headers(admin_token: str) -> dict[str, str]:
    """Return HTTP headers with the admin bearer token."""
    return {"Authorization": f"Bearer {admin_token}"}
