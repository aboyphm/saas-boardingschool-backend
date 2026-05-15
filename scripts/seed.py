"""
Database seed script.

Creates representative demo data for development and staging environments.
Run with: docker-compose exec backend python scripts/seed.py
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_password_hash
from app.domains.academics.models import AcademicYear, ClassRoom, Subject
from app.domains.dormitory.models import DormitoryBuilding, DormitoryRoom
from app.domains.finance.models import FeeCategory
from app.domains.students.models import Student
from app.domains.teachers.models import Teacher
from app.domains.tenants.models import Tenant
from app.domains.users.models import User
from app.shared.enums import (
    DormitoryRoomStatus,
    DormitoryRoomType,
    EmploymentType,
    Gender,
    SubscriptionPlan,
    SubjectType,
    TenantStatus,
    UserRole,
    BillingCycle,
)


async def seed(session: AsyncSession) -> None:
    print("Starting seed process...")

    # ─── Super admin ──────────────────────────────────────────────────────────
    super_admin = User(
        id=uuid.uuid4(),
        email="superadmin@platform.com",
        full_name="Super Administrator",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
        is_verified=True,
        password_hash=get_password_hash("SuperAdmin@123"),
    )
    session.add(super_admin)
    print(f"  Created super admin: {super_admin.email}")

    # ─── Tenants ──────────────────────────────────────────────────────────────
    tenants: list[Tenant] = []
    for i, (name, slug) in enumerate([
        ("Pesantren Al-Fikri", "al-fikri"),
        ("Madrasah Nurul Ilmi", "nurul-ilmi"),
    ]):
        tenant = Tenant(
            id=uuid.uuid4(),
            name=name,
            slug=slug,
            subdomain=slug,
            status=TenantStatus.ACTIVE,
            plan=SubscriptionPlan.PROFESSIONAL,
            contact_email=f"admin@{slug}.sch.id",
            contact_phone=f"+6281200000{i}",
            city="Jakarta",
            country="Indonesia",
            timezone="Asia/Jakarta",
        )
        session.add(tenant)
        tenants.append(tenant)
    print(f"  Created {len(tenants)} tenants")

    await session.flush()

    # ─── Tenant admins ────────────────────────────────────────────────────────
    for tenant in tenants:
        admin = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email=f"admin@{tenant.slug}.sch.id",
            full_name=f"Admin {tenant.name}",
            role=UserRole.TENANT_ADMIN,
            is_active=True,
            is_verified=True,
            password_hash=get_password_hash("Admin@123456"),
        )
        session.add(admin)

        # ─── Teachers ─────────────────────────────────────────────────────────
        for j in range(3):
            teacher_user = User(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                email=f"teacher{j + 1}@{tenant.slug}.sch.id",
                full_name=f"Ustadz/Ustadzah {j + 1} - {tenant.name}",
                role=UserRole.TEACHER,
                is_active=True,
                is_verified=True,
                password_hash=get_password_hash("Teacher@123"),
            )
            session.add(teacher_user)
            await session.flush()

            teacher = Teacher(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                user_id=teacher_user.id,
                nip=f"NIP-{tenant.slug[:3].upper()}-{j + 1:03d}",
                full_name=teacher_user.full_name,
                gender=Gender.MALE if j % 2 == 0 else Gender.FEMALE,
                specialization="Mathematics" if j == 0 else ("Quran" if j == 1 else "Islamic Studies"),
                employment_type=EmploymentType.FULL_TIME,
                join_date=date.today() - timedelta(days=365 * (j + 1)),
            )
            session.add(teacher)

    await session.flush()

    # ─── Academic years & classes ─────────────────────────────────────────────
    for tenant in tenants:
        year = AcademicYear(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            name="2024/2025",
            start_date=date(2024, 7, 1),
            end_date=date(2025, 6, 30),
            is_active=True,
        )
        session.add(year)
        await session.flush()

        classes = []
        for grade in ["VII", "VIII", "IX"]:
            classroom = ClassRoom(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                academic_year_id=year.id,
                name=f"Kelas {grade}-A",
                grade_level=grade,
                capacity=30,
                current_count=0,
            )
            session.add(classroom)
            classes.append(classroom)
        await session.flush()

        # ─── Subjects ─────────────────────────────────────────────────────────
        subjects_data = [
            ("MTK", "Matematika", SubjectType.GENERAL),
            ("QRN", "Tahfidz Quran", SubjectType.QURAN),
            ("FQH", "Fiqih", SubjectType.RELIGIOUS),
            ("BHS", "Bahasa Arab", SubjectType.RELIGIOUS),
        ]
        for code, name, subject_type in subjects_data:
            subject = Subject(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                code=f"{code}-{tenant.slug[:3].upper()}",
                name=name,
                credit_hours=2,
                subject_type=subject_type,
            )
            session.add(subject)

        # ─── Students ─────────────────────────────────────────────────────────
        for k, classroom in enumerate(classes):
            for m in range(5):
                student_number = k * 5 + m + 1
                student = Student(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    nis=f"NIS-{tenant.slug[:3].upper()}-{student_number:04d}",
                    full_name=f"Santri {student_number} {tenant.name}",
                    gender=Gender.MALE if m % 2 == 0 else Gender.FEMALE,
                    birth_date=date(2010 + k, 1 + m, 10),
                    religion="Islam",
                    nationality="Indonesian",
                    class_id=classroom.id,
                    enrollment_date=date(2024, 7, 15),
                    academic_year="2024/2025",
                )
                session.add(student)
                classroom.current_count += 1
            session.add(classroom)

        # ─── Dormitory ────────────────────────────────────────────────────────
        for gender, gender_label in [(Gender.MALE, "Putra"), (Gender.FEMALE, "Putri")]:
            building = DormitoryBuilding(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                name=f"Asrama {gender_label} {tenant.name}",
                gender_type=gender,
                capacity=100,
            )
            session.add(building)
            await session.flush()

            for room_num in range(1, 4):
                room = DormitoryRoom(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    building_id=building.id,
                    room_number=f"{gender_label[0]}-{room_num:02d}",
                    floor=1,
                    capacity=8,
                    current_occupancy=0,
                    status=DormitoryRoomStatus.AVAILABLE,
                    room_type=DormitoryRoomType.STANDARD,
                    facilities=["beds", "desk", "wardrobe", "AC"],
                )
                session.add(room)

        # ─── Fee categories ───────────────────────────────────────────────────
        fee_data = [
            ("SPP Bulanan", 500_000, True, BillingCycle.MONTHLY),
            ("Biaya Asrama", 300_000, True, BillingCycle.MONTHLY),
            ("Biaya Daftar Ulang", 1_000_000, False, BillingCycle.YEARLY),
        ]
        for fname, amount, recurring, cycle in fee_data:
            fee = FeeCategory(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                name=fname,
                amount=amount,
                is_recurring=recurring,
                billing_cycle=cycle,
            )
            session.add(fee)

    await session.flush()
    print("  Seed data inserted successfully.")
    print("\nSeed accounts:")
    print("  Super Admin : superadmin@platform.com / SuperAdmin@123")
    print("  Tenant Admin: admin@al-fikri.sch.id / Admin@123456")
    print("  Tenant Admin: admin@nurul-ilmi.sch.id / Admin@123456")


async def main() -> None:
    async with get_db_session() as session:
        await seed(session)
        print("\nSeed completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
