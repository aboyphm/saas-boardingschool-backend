from fastapi import APIRouter

from app.api.v1.endpoints import (
    academics,
    admin_apps,
    admissions,
    assets,
    attendance,
    auth,
    certificates,
    cors as cors_ep,
    dormitory,
    exams,
    finance,
    hr,
    notifications,
    reports,
    students,
    subscriptions,
    teachers,
    tenants,
    users,
)

api_router = APIRouter()

api_router.include_router(admin_apps.router, prefix="/admin-apps", tags=["Admin Apps"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(students.router, prefix="/students", tags=["Students"])
api_router.include_router(teachers.router, prefix="/teachers", tags=["Teachers"])
api_router.include_router(academics.router, prefix="/academics", tags=["Academics"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["Attendance"])
api_router.include_router(dormitory.router, prefix="/dormitory", tags=["Dormitory"])
api_router.include_router(finance.router, prefix="/finance", tags=["Finance"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(hr.router, prefix="/hr", tags=["HR"])
api_router.include_router(exams.router, prefix="/exams", tags=["Exams"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["Subscriptions"])
api_router.include_router(admissions.router, prefix="/admissions", tags=["Admissions"])
api_router.include_router(assets.router, prefix="/assets", tags=["Assets"])
api_router.include_router(certificates.router, prefix="/certificates", tags=["Certificates"])
api_router.include_router(cors_ep.router, prefix="/cors-origins", tags=["CORS"])
