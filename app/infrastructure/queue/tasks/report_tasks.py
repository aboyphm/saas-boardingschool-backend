from __future__ import annotations

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    name="app.infrastructure.queue.tasks.report_tasks.generate_weekly_summary",
)
def generate_weekly_summary() -> dict:
    """
    Scheduled task: generate a weekly summary report for all active tenants.
    Runs every Monday at 06:00 WIB.
    """
    logger.info("Running weekly summary report generation")
    # TODO: Query active tenants, generate attendance + finance summaries,
    #       and dispatch summary emails to tenant admins.
    return {"status": "scheduled"}


@shared_task(
    name="app.infrastructure.queue.tasks.report_tasks.generate_monthly_report",
    max_retries=2,
)
def generate_monthly_report(tenant_id: str, year: int, month: int) -> dict:
    """
    Generate a full monthly operational report for a specific tenant.

    :param tenant_id: Target tenant UUID string.
    :param year: Report year (e.g., 2025).
    :param month: Report month (1–12).
    """
    logger.info("Generating monthly report for tenant=%s (%d-%02d)", tenant_id, year, month)
    # TODO: Generate PDF report using WeasyPrint or ReportLab and upload to S3/R2.
    return {"status": "generated", "tenant_id": tenant_id, "period": f"{year}-{month:02d}"}
