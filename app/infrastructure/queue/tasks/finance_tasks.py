from __future__ import annotations

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    name="app.infrastructure.queue.tasks.finance_tasks.generate_monthly_invoices",
)
def generate_monthly_invoices() -> dict:
    """
    Scheduled task: auto-generate monthly invoices for all active students
    across all active tenants based on recurring fee categories.

    Runs on the 1st of each month at 07:00 WIB.
    """
    logger.info("Running monthly invoice generation task")
    # TODO: Query active tenants, iterate fee categories with is_recurring=True
    #       and billing_cycle=MONTHLY, create draft invoices for each student,
    #       and optionally send them automatically.
    return {"status": "scheduled"}


@shared_task(
    name="app.infrastructure.queue.tasks.finance_tasks.mark_overdue_invoices",
)
def mark_overdue_invoices() -> dict:
    """
    Scheduled task: transition all ``SENT`` invoices past their due date to
    ``OVERDUE`` status.

    Runs daily at 01:00 WIB.
    """
    import asyncio
    from datetime import UTC, date, datetime
    from app.core.database import get_db_session
    from app.domains.finance.models import Invoice
    from app.shared.enums import InvoiceStatus
    from sqlalchemy import select

    async def _run() -> int:
        async with get_db_session() as session:
            stmt = (
                select(Invoice)
                .where(
                    Invoice.status == InvoiceStatus.SENT,
                    Invoice.due_date < date.today(),
                )
            )
            result = await session.execute(stmt)
            invoices = result.scalars().all()
            count = 0
            for invoice in invoices:
                invoice.status = InvoiceStatus.OVERDUE
                session.add(invoice)
                count += 1
            return count

    updated = asyncio.run(_run())
    logger.info("Marked %d invoices as overdue", updated)
    return {"status": "completed", "updated_count": updated}
