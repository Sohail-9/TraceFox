"""Structured logging configuration for TraceFox services."""

from __future__ import annotations

import logging
from typing import Optional

from services.shared.config import ConfigurationError, get_settings


def setup_logging(level: Optional[int] = None) -> None:
    try:
        environment = get_settings().environment
    except ConfigurationError:
        environment = "unknown"

    effective_level = level
    if effective_level is None:
        effective_level = logging.DEBUG if environment == "local" else logging.INFO
    logging.basicConfig(
        level=effective_level,
        format=(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s | "
            "trace_id=%(trace_id)s span_id=%(span_id)s"
        ),
    )


class ContextFilter(logging.Filter):
    """Provide default span/trace identifiers for structured logs."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        if not hasattr(record, "trace_id"):
            record.trace_id = "0000000000000000"
        if not hasattr(record, "span_id"):
            record.span_id = "0000000000000000"
        return True


setup_logging()
logging.getLogger().addFilter(ContextFilter())
logging.getLogger("neo4j").setLevel(logging.WARNING)
