"""Structured logging configuration for TraceFox services."""

from __future__ import annotations

import logging
from typing import Optional

from services.shared.config import ConfigurationError, get_settings

class ColoredFormatter(logging.Formatter):
    COLOR_CODES = {
        logging.DEBUG: "\033[36m",    # Cyan
        logging.INFO: "\033[32m",     # Green
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[35m", # Magenta
    }
    RESET_CODE = "\033[0m"

    def format(self, record):
        level_color = self.COLOR_CODES.get(record.levelno, self.RESET_CODE)
        record.levelname = f"{level_color}{record.levelname}{self.RESET_CODE}"
        return super().format(record)

_RECORD_FACTORY_INSTALLED = False


def _install_record_factory() -> None:
    global _RECORD_FACTORY_INSTALLED
    if _RECORD_FACTORY_INSTALLED:
        return

    previous_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):  # type: ignore[no-untyped-def]
        record = previous_factory(*args, **kwargs)
        if not hasattr(record, "trace_id"):
            record.trace_id = "0000000000000000"
        if not hasattr(record, "span_id"):
            record.span_id = "0000000000000000"
        return record

    logging.setLogRecordFactory(record_factory)
    _RECORD_FACTORY_INSTALLED = True


def setup_logging(level: Optional[int] = None) -> None:
    try:
        environment = get_settings().environment
    except ConfigurationError:
        environment = "unknown"

    effective_level = level
    if effective_level is None:
        effective_level = logging.DEBUG if environment == "local" else logging.INFO

    _install_record_factory()

    handler = logging.StreamHandler()
    handler.setFormatter(ColoredFormatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s | trace_id=%(trace_id)s span_id=%(span_id)s"
    ))
    logging.basicConfig(level=effective_level, handlers=[handler])


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
