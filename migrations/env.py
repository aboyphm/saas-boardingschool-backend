from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# Import all models so Alembic can detect them
from app.core.database import Base
from app.domains.tenants.models import Tenant, TenantBranding  # noqa: F401
from app.domains.users.models import User, RolePermission, UserSession, AdminAppsTenant  # noqa: F401
from app.domains.auth.models import PasswordResetToken  # noqa: F401
from app.domains.students.models import Student, StudentParent  # noqa: F401
from app.domains.teachers.models import Teacher  # noqa: F401
from app.domains.academics.models import AcademicYear, ClassRoom, Subject, Assignment, Grade  # noqa: F401
from app.domains.attendance.models import AttendanceRecord, LeaveRequest  # noqa: F401
from app.domains.dormitory.models import DormitoryBuilding, DormitoryRoom, DormitoryAssignment, DormitorySupervisor  # noqa: F401
from app.domains.finance.models import FeeCategory, Invoice, Payment, PayrollRecord  # noqa: F401
from app.domains.notifications.models import NotificationTemplate, NotificationLog  # noqa: F401

config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    from app.core.config import get_settings
    return get_settings().DATABASE_URL


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using the async engine."""
    connectable = create_async_engine(get_url(), poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
