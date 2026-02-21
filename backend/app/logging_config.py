"""Structured logging configuration.

JSON format in production, readable format in development.
"""

import logging
import sys
from datetime import datetime, timezone

from app.config import settings


class JSONFormatter(logging.Formatter):
    """JSON log formatter for production."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "restaurant_id"):
            log_entry["restaurant_id"] = record.restaurant_id  # type: ignore[attr-defined]
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id  # type: ignore[attr-defined]
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms  # type: ignore[attr-defined]

        # Add exception info if present
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


class DevFormatter(logging.Formatter):
    """Readable log formatter for development."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        extras = []
        if hasattr(record, "restaurant_id"):
            extras.append(f"r={record.restaurant_id}")  # type: ignore[attr-defined]
        if hasattr(record, "duration_ms"):
            extras.append(f"{record.duration_ms}ms")  # type: ignore[attr-defined]
        extra_str = f" [{', '.join(extras)}]" if extras else ""
        return f"{timestamp} {record.levelname:<7} {record.name}: {record.getMessage()}{extra_str}"


def setup_logging() -> None:
    """Configure logging based on environment."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)

    if settings.environment == "production":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(DevFormatter())

    root_logger.addHandler(handler)

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
