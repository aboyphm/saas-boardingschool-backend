from fastapi import APIRouter

from app.api.v1.endpoints import (
    academics,
    admin_apps,
    attendance,
    auth,
    dormitory,
    finance,
    notifications,
    reports,
    students,
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
