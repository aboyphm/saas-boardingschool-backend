from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

EventHandler = Callable[[dict], Coroutine[Any, Any, None]]

# ─── Well-known event names ───────────────────────────────────────────────────
class Events:
    STUDENT_ENROLLED = "student.enrolled"
    ATTENDANCE_MARKED = "attendance.marked"
    INVOICE_CREATED = "invoice.created"
    PAYMENT_RECEIVED = "payment.received"
    LEAVE_APPROVED = "leave.approved"
    TENANT_CREATED = "tenant.created"
    USER_REGISTERED = "user.registered"


class EventBus:
    """
    Simple in-process async event bus.

    This is intentionally lightweight — it is suitable for synchronising
    domain events within a single request/worker process. For cross-process
    events, use Celery tasks directly.

    Usage::

        bus = EventBus.get_instance()
        bus.subscribe("student.enrolled", my_handler)
        await bus.publish("student.enrolled", {"student_id": "..."})
    """

    _instance: "EventBus | None" = None

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    @classmethod
    def get_instance(cls) -> "EventBus":
        """Return the process-wide singleton event bus."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """Register an async handler for the given event name."""
        self._handlers[event_name].append(handler)
        logger.debug("EventBus: subscribed to '%s'", event_name)

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        """Remove a previously registered handler."""
        if event_name in self._handlers:
            try:
                self._handlers[event_name].remove(handler)
            except ValueError:
                pass

    async def publish(self, event_name: str, payload: dict) -> None:
        """
        Dispatch an event to all registered handlers concurrently.

        Handler exceptions are caught and logged but do not propagate —
        a failing handler must not prevent other handlers from executing.

        :param event_name: Dot-separated event identifier (e.g., ``student.enrolled``).
        :param payload: Arbitrary dict of event data.
        """
        handlers = self._handlers.get(event_name, [])
        if not handlers:
            return

        logger.debug("EventBus: publishing '%s' to %d handler(s)", event_name, len(handlers))

        tasks = [asyncio.ensure_future(handler(payload)) for handler in handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for handler, result in zip(handlers, results):
            if isinstance(result, Exception):
                logger.error(
                    "EventBus: handler %s failed for event '%s': %s",
                    handler.__name__,
                    event_name,
                    result,
                )


# Module-level convenience instance
event_bus = EventBus.get_instance()
