from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN_APPS = "admin_apps"
    TENANT_ADMIN = "tenant_admin"
    OWNER = "owner"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"
    FINANCE_STAFF = "finance_staff"
    BOARDING_SUPERVISOR = "boarding_supervisor"
    ADMIN_STAFF = "admin_staff"


class TenantStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    EXPIRED = "expired"


class SubscriptionPlan(str, enum.Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class StudentStatus(str, enum.Enum):
    ACTIVE = "active"
    GRADUATED = "graduated"
    DROPPED_OUT = "dropped_out"
    SUSPENDED = "suspended"
    ON_LEAVE = "on_leave"


class AttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"
    SICK = "sick"


class AttendanceInputMethod(str, enum.Enum):
    QR = "qr"
    MANUAL = "manual"
    RFID = "rfid"
    BIOMETRIC = "biometric"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class BillingCycle(str, enum.Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"
    ONE_TIME = "one_time"


class NotificationChannel(str, enum.Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    PUSH = "push"
    SMS = "sms"
    IN_APP = "in_app"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    READ = "read"


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"


class DormitoryRoomStatus(str, enum.Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"


class DormitoryRoomType(str, enum.Enum):
    STANDARD = "standard"
    VIP = "vip"


class LeaveRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class EmploymentType(str, enum.Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    HONORARY = "honorary"


class SubjectType(str, enum.Enum):
    GENERAL = "general"
    RELIGIOUS = "religious"
    QURAN = "quran"
    EXTRACURRICULAR = "extracurricular"


class ParentRelationship(str, enum.Enum):
    FATHER = "father"
    MOTHER = "mother"
    GUARDIAN = "guardian"


class PayrollStatus(str, enum.Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    PAID = "paid"


class Semester(int, enum.Enum):
    FIRST = 1
    SECOND = 2
