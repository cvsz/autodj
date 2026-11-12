"""JSON structured logging for CamfrogAutoDJ.

Provides a JSON formatter for structured log output compatible with
Loki, Grafana, Elasticsearch, and other log aggregation systems.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any, Optional

from .config import Config


class JsonFormatter(logging.Formatter):
    """JSON log formatter with structured fields.

    Output format:
    {
        "timestamp": "2026-11-12T17:51:31.123456+07:00",
        "level": "INFO",
        "logger": "autodj",
        "message": "config reloaded",
        "request_id": "req-123",
        "user": "testuser",
        "track_id": "track-456",
        "generation": 42,
        "extra_field": "value"
    }
    """

    # Standard fields that are always included
    STANDARD_FIELDS = {
        "timestamp",
        "level",
        "logger",
        "message",
        "module",
        "function",
        "line",
    }

    def __init__(
        self,
        *,
        include_extra: bool = True,
        extra_fields: Optional[list[str]] = None,
        timestamp_format: str = "iso",
    ):
        """
        Args:
            include_extra: Whether to include extra fields from LogRecord.__dict__
            extra_fields: List of extra field names to include (if None, includes all)
            timestamp_format: "iso" for ISO 8601, "epoch" for Unix timestamp
        """
        super().__init__()
        self.include_extra = include_extra
        self.extra_fields = set(extra_fields) if extra_fields else None
        self.timestamp_format = timestamp_format

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        # Base log entry
        log_entry: dict[str, Any] = {
            "timestamp": self._format_timestamp(record.created),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add stack info if present
        if record.stack_info:
            log_entry["stack"] = self.formatStack(record.stack_info)

        # Add extra fields from record.__dict__
        if self.include_extra:
            self._add_extra_fields(log_entry, record)

        return json.dumps(log_entry, ensure_ascii=False, separators=(",", ":"))

    def _format_timestamp(self, created: float) -> str:
        """Format timestamp according to timestamp_format."""
        if self.timestamp_format == "epoch":
            return str(created)
        # ISO 8601 with microseconds
        return (
            time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(created))
            + f".{int(created * 1_000_000) % 1_000_000:06d}"
        )

    def _add_extra_fields(self, log_entry: dict[str, Any], record: logging.LogRecord) -> None:
        """Add extra fields from LogRecord to log entry."""
        # Known structured fields from Engine (always included when extra_fields is None)
        known_fields = {
            "request_id",
            "delivery_id",
            "user",
            "track_id",
            "generation",
            "attempt_id",
            "category",
            "stage",
            "state",
        }

        for key, value in record.__dict__.items():
            # Skip standard logging fields
            if key in self.STANDARD_FIELDS:
                continue
            # Skip internal fields
            if key.startswith("_"):
                continue
            # Skip args and message (already in message)
            if key in ("args", "msg"):
                continue

            # Include logic:
            # - If extra_fields is None: include known_fields + any other non-standard fields
            # - If extra_fields is set: only include fields in extra_fields (known_fields only if explicitly listed)
            should_include = False
            if self.extra_fields is None:
                # Include known fields and any other non-standard fields
                should_include = True
            elif key in self.extra_fields:
                # Explicitly listed in extra_fields
                should_include = True
            elif key in known_fields and self.extra_fields is not None:
                # Known field but not explicitly listed - exclude
                should_include = False
            else:
                # Not a known field and not explicitly listed
                should_include = False

            if should_include:
                # Ensure JSON serializable
                try:
                    json.dumps(value)
                    log_entry[key] = value
                except (TypeError, ValueError):
                    log_entry[key] = str(value)


def configure_json_logging(
    config: Config,
    *,
    level: int = logging.INFO,
    stream: Optional[Any] = None,
) -> logging.Handler:
    """Configure JSON logging for the application.

    Args:
        config: Config instance with log_json and log_json_fields settings
        level: Logging level
        stream: Output stream (default: sys.stdout)

    Returns:
        The configured StreamHandler
    """
    if stream is None:
        stream = sys.stdout

    handler = logging.StreamHandler(stream)
    handler.setLevel(level)

    # Determine extra fields to include
    extra_fields = None
    if hasattr(config, "log_json_fields") and config.log_json_fields:
        extra_fields = config.log_json_fields

    formatter = JsonFormatter(
        include_extra=True,
        extra_fields=extra_fields,
        timestamp_format="iso",
    )
    handler.setFormatter(formatter)

    # Get root logger and add handler
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    return handler


def add_json_file_handler(
    config: Config,
    log_path: str,
    *,
    level: int = logging.INFO,
    max_bytes: int = 1_000_000,
    backup_count: int = 3,
) -> logging.Handler:
    """Add a rotating file handler with JSON formatting.

    Args:
        config: Config instance
        log_path: Path to log file
        level: Logging level
        max_bytes: Max file size before rotation
        backup_count: Number of backup files to keep

    Returns:
        The configured RotatingFileHandler
    """
    from logging.handlers import RotatingFileHandler

    handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)

    extra_fields = None
    if hasattr(config, "log_json_fields") and config.log_json_fields:
        extra_fields = config.log_json_fields

    formatter = JsonFormatter(
        include_extra=True,
        extra_fields=extra_fields,
        timestamp_format="iso",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    return handler
