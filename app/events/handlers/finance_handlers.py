from __future__ import annotations

from app.core.logging import get_logger
from app.events.event_bus import Events, event_bus

logger = get_logger(__name__)


async def on_payment_received(payload: dict) -> None:
    """
    Handle the ``payment.received`` event.

    Responsibilities:
    - Enqueue a payment confirmation notification to the parent.
    - Update outstanding balance in cache.
    """
    invoice_id = payload.get("invoice_id")
    amount = payload.get("amount")
    logger.info("payment.received: invoice_id=%s amount=%s", invoice_id, amount)
    # TODO: Enqueue payment confirmation WhatsApp/email task.


async def on_invoice_created(payload: dict) -> None:
    """
    Handle the ``invoice.created`` event.

    Responsibilities:
    - Notify finance staff via in-app notification.
    """
    invoice_id = payload.get("invoice_id")
    student_id = payload.get("student_id")
    logger.info("invoice.created: invoice_id=%s student_id=%s", invoice_id, student_id)


def register_finance_handlers() -> None:
    """Register all finance domain event handlers with the event bus."""
    event_bus.subscribe(Events.PAYMENT_RECEIVED, on_payment_received)
    event_bus.subscribe(Events.INVOICE_CREATED, on_invoice_created)
