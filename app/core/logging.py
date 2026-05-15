from __future__ import annotations

import logging
import sys
from typing import Any

try:
    import structlog

    _USE_STRUCTLOG = True
except ImportError:
    _USE_STRUCTLOG = False


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure application-wide structured logging.

    When ``structlog`` is available, JSON-formatted structured logs are emitted.
    Otherwise the standard library formatter is used as a fallback.

    :param log_level: One of DEBUG, INFO, WARNING, ERROR, CRITICAL.
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    if _USE_STRUCTLOG:
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
            cache_logger_on_first_use=True,
        )

    # Always configure stdlib so that third-party libraries are captured.
    logging.basicConfig(
        level=numeric_level,
        stream=sys.stdout,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    # Suppress overly verbose third-party loggers in production.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> Any:
    """
    Return a logger for the given module name.

    Returns a ``structlog`` bound logger when available, falling back to the
    standard library logger otherwise.

    :param name: Usually ``__name__`` of the calling module.
    """
    if _USE_STRUCTLOG:
        return structlog.get_logger(name)
    return logging.getLogger(name)
