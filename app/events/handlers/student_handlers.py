from __future__ import annotations

from app.core.logging import get_logger
from app.events.event_bus import Events, event_bus

logger = get_logger(__name__)


async def on_student_enrolled(payload: dict) -> None:
    """
    Handle the ``student.enrolled`` event.

    Responsibilities:
    - Enqueue a welcome notification to the student's parent(s).
    - Increment the classroom's ``current_count``.
    """
    student_id = payload.get("student_id")
    tenant_id = payload.get("tenant_id")
    logger.info("student.enrolled: student_id=%s tenant_id=%s", student_id, tenant_id)
    # TODO: Enqueue welcome notification task.


def register_student_handlers() -> None:
    """Register all student domain event handlers with the event bus."""
    event_bus.subscribe(Events.STUDENT_ENROLLED, on_student_enrolled)
