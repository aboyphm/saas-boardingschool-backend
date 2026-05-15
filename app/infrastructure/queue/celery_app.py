from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "boarding_school_saas",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.infrastructure.queue.tasks.notification_tasks",
        "app.infrastructure.queue.tasks.report_tasks",
        "app.infrastructure.queue.tasks.finance_tasks",
    ],
)

# ─── Celery configuration ─────────────────────────────────────────────────────
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Jakarta",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    task_soft_time_limit=300,   # 5-minute soft limit per task
    task_time_limit=600,        # 10-minute hard limit per task
    worker_max_tasks_per_child=1000,
)

# ─── Task routing ─────────────────────────────────────────────────────────────
celery_app.conf.task_routes = {
    "app.infrastructure.queue.tasks.notification_tasks.*": {"queue": "notifications"},
    "app.infrastructure.queue.tasks.report_tasks.*": {"queue": "reports"},
    "app.infrastructure.queue.tasks.finance_tasks.*": {"queue": "finance"},
}

# ─── Beat schedule ────────────────────────────────────────────────────────────
celery_app.conf.beat_schedule = {
    # Remind teachers/parents about attendance at 08:00 WIB daily
    "daily-attendance-reminder": {
        "task": "app.infrastructure.queue.tasks.notification_tasks.send_daily_attendance_reminder",
        "schedule": crontab(hour=8, minute=0),
        "options": {"queue": "notifications"},
    },
    # Auto-generate monthly invoices on the 1st of every month at 07:00
    "monthly-invoice-generation": {
        "task": "app.infrastructure.queue.tasks.finance_tasks.generate_monthly_invoices",
        "schedule": crontab(day_of_month=1, hour=7, minute=0),
        "options": {"queue": "finance"},
    },
    # Generate weekly summary reports every Monday at 06:00
    "weekly-summary-report": {
        "task": "app.infrastructure.queue.tasks.report_tasks.generate_weekly_summary",
        "schedule": crontab(day_of_week=1, hour=6, minute=0),
        "options": {"queue": "reports"},
    },
    # Mark overdue invoices daily at 01:00
    "mark-overdue-invoices": {
        "task": "app.infrastructure.queue.tasks.finance_tasks.mark_overdue_invoices",
        "schedule": crontab(hour=1, minute=0),
        "options": {"queue": "finance"},
    },
}
