from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    name="app.infrastructure.queue.tasks.notification_tasks.send_email_notification",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def send_email_notification(
    self: Any,
    recipient: str,
    subject: str,
    body: str,
    template_id: str | None = None,
) -> dict:
    """
    Send a single email notification.

    Uses exponential backoff retry (up to 3 attempts) on any exception.
    In production, integrate with SendGrid, AWS SES, or an SMTP relay.

    :param recipient: Destination email address.
    :param subject: Email subject line.
    :param body: Rendered HTML or plain-text body.
    :param template_id: Optional ID of a stored notification template.
    :returns: Delivery result dict with ``status`` and ``message_id``.
    """
    try:
        logger.info("Sending email to %s (subject: %s)", recipient, subject)
        # TODO: Integrate with email provider (SendGrid, AWS SES, SMTP).
        # Example: sendgrid_client.send(to=recipient, subject=subject, html=body)

        _update_notification_log(template_id, "sent")
        return {"status": "sent", "recipient": recipient}
    except Exception as exc:
        logger.error("Email delivery failed for %s: %s", recipient, exc)
        _update_notification_log(template_id, "failed", error=str(exc))
        raise


@shared_task(
    bind=True,
    name="app.infrastructure.queue.tasks.notification_tasks.send_whatsapp_notification",
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_whatsapp_notification(
    self: Any,
    phone: str,
    message: str,
    template_id: str | None = None,
) -> dict:
    """
    Send a WhatsApp message via the configured API.

    :param phone: Destination phone number in E.164 format (+628xx).
    :param message: Message body (max 4096 chars).
    :param template_id: Optional template ID for WhatsApp Business templates.
    """
    try:
        logger.info("Sending WhatsApp to %s", phone)
        # TODO: Integrate with WhatsApp Business API / Twilio / etc.

        _update_notification_log(template_id, "sent")
        return {"status": "sent", "phone": phone}
    except Exception as exc:
        logger.error("WhatsApp delivery failed for %s: %s", phone, exc)
        _update_notification_log(template_id, "failed", error=str(exc))
        raise


@shared_task(
    name="app.infrastructure.queue.tasks.notification_tasks.send_bulk_notification",
    max_retries=3,
    default_retry_delay=120,
)
def send_bulk_notification(notification_ids: list[str]) -> dict:
    """
    Process multiple pending notification log entries in a single task.

    Dispatches individual sub-tasks per channel to decouple delivery logic.

    :param notification_ids: List of NotificationLog UUIDs to process.
    :returns: Dict with counts of dispatched and failed deliveries.
    """
    dispatched = 0
    failed = 0

    for notification_id in notification_ids:
        try:
            _dispatch_single_notification(notification_id)
            dispatched += 1
        except Exception as exc:
            logger.error("Failed to dispatch notification %s: %s", notification_id, exc)
            failed += 1

    return {"dispatched": dispatched, "failed": failed, "total": len(notification_ids)}


@shared_task(
    name="app.infrastructure.queue.tasks.notification_tasks.send_daily_attendance_reminder",
)
def send_daily_attendance_reminder() -> dict:
    """
    Scheduled task: notify all teachers to mark attendance for today.
    Runs daily at 08:00 WIB via the Celery beat schedule.
    """
    logger.info("Running daily attendance reminder task")
    # TODO: Query active tenants and teachers, enqueue per-teacher reminders.
    return {"status": "scheduled"}


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _update_notification_log(
    notification_id: str | None,
    status: str,
    error: str | None = None,
) -> None:
    """Update the notification log record status (fire-and-forget, sync)."""
    if not notification_id:
        return
    try:
        from datetime import UTC, datetime
        import asyncio
        from app.core.database import get_db_session
        from app.domains.notifications.models import NotificationLog
        from sqlalchemy import select

        async def _update() -> None:
            async with get_db_session() as session:
                stmt = select(NotificationLog).where(
                    NotificationLog.id == notification_id
                )
                result = await session.execute(stmt)
                log = result.scalar_one_or_none()
                if log:
                    log.status = status
                    if status == "sent":
                        log.sent_at = datetime.now(UTC)
                    if error:
                        log.error_message = error
                        log.retry_count += 1
                    session.add(log)

        asyncio.run(_update())
    except Exception as exc:
        logger.warning("Could not update notification log %s: %s", notification_id, exc)


def _dispatch_single_notification(notification_id: str) -> None:
    """Fetch a notification log entry and dispatch the appropriate sub-task."""
    # This runs synchronously inside a Celery worker.
    import asyncio
    from app.core.database import get_db_session
    from app.domains.notifications.models import NotificationLog
    from app.shared.enums import NotificationChannel
    from sqlalchemy import select

    async def _fetch() -> NotificationLog | None:
        async with get_db_session() as session:
            stmt = select(NotificationLog).where(
                NotificationLog.id == notification_id
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    log = asyncio.run(_fetch())
    if log is None:
        logger.warning("Notification log %s not found", notification_id)
        return

    if log.channel == NotificationChannel.EMAIL:
        send_email_notification.delay(
            recipient="",  # Would load from recipient_user_id
            subject=log.subject or "",
            body=log.body,
            template_id=str(log.id),
        )
    elif log.channel == NotificationChannel.WHATSAPP:
        send_whatsapp_notification.delay(
            phone="",  # Would load from recipient_user_id
            message=log.body,
            template_id=str(log.id),
        )
