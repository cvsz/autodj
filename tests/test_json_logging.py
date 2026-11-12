"""Tests for JSON structured logging."""

from __future__ import annotations

import io
import json
import logging
import sys

import pytest

from camfrog_autodj.config import Config
from camfrog_autodj.logging_json import JsonFormatter, add_json_file_handler, configure_json_logging


class TestJsonFormatter:
    """Tests for JsonFormatter."""

    def test_basic_format(self):
        """Test basic JSON formatting."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test"
        record.funcName = "test_func"

        output = formatter.format(record)
        data = json.loads(output)

        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "Test message"
        assert data["module"] == "test"
        assert data["function"] == "test_func"
        assert data["line"] == 42
        assert "timestamp" in data

    def test_format_with_extra_fields(self):
        """Test formatting with extra fields from record."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test"
        record.funcName = "test_func"
        record.request_id = "req-123"
        record.user = "testuser"
        record.track_id = "track-456"

        output = formatter.format(record)
        data = json.loads(output)

        assert data["request_id"] == "req-123"
        assert data["user"] == "testuser"
        assert data["track_id"] == "track-456"

    def test_format_with_exception(self):
        """Test formatting with exception info."""
        formatter = JsonFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )
        record.module = "test"
        record.funcName = "test_func"

        output = formatter.format(record)
        data = json.loads(output)

        assert data["level"] == "ERROR"
        assert "exception" in data
        assert "ValueError: test error" in data["exception"]

    def test_format_with_stack_info(self):
        """Test formatting with stack info."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test"
        record.funcName = "test_func"
        record.stack_info = "Stack trace here"

        output = formatter.format(record)
        data = json.loads(output)

        assert "stack" in data
        assert data["stack"] == "Stack trace here"

    def test_extra_fields_filter(self):
        """Test filtering extra fields."""
        formatter = JsonFormatter(extra_fields=["request_id", "user"])
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test"
        record.funcName = "test_func"
        record.request_id = "req-123"
        record.user = "testuser"
        record.track_id = "track-456"  # Should be filtered out

        output = formatter.format(record)
        data = json.loads(output)

        assert data["request_id"] == "req-123"
        assert data["user"] == "testuser"
        assert "track_id" not in data

    def test_non_serializable_extra(self):
        """Test handling of non-JSON-serializable extra fields."""
        formatter = JsonFormatter()

        class NonSerializable:
            pass

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test"
        record.funcName = "test_func"
        record.bad_field = NonSerializable()

        output = formatter.format(record)
        data = json.loads(output)

        # Should convert to string representation
        assert "bad_field" in data
        assert "NonSerializable" in data["bad_field"]


class TestConfigureJsonLogging:
    """Tests for configure_json_logging."""

    def test_configure_json_logging_stdout(self):
        """Test configuring JSON logging to stdout."""
        cfg = Config()
        cfg.log_json = True

        stream = io.StringIO()
        handler = configure_json_logging(cfg, level=logging.INFO, stream=stream)

        logger = logging.getLogger("test")
        logger.info("Test message", extra={"request_id": "req-123"})

        output = stream.getvalue().strip()
        data = json.loads(output)

        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert data["request_id"] == "req-123"

        # Cleanup
        logging.getLogger().removeHandler(handler)

    def test_configure_json_logging_with_custom_fields(self):
        """Test configuring JSON logging with custom extra fields."""
        cfg = Config()
        cfg.log_json = True
        cfg.log_json_fields = ["custom_field"]

        stream = io.StringIO()
        handler = configure_json_logging(cfg, level=logging.INFO, stream=stream)

        logger = logging.getLogger("test")
        logger.info("Test message", extra={"custom_field": "value", "other_field": "ignored"})

        output = stream.getvalue().strip()
        data = json.loads(output)

        assert data["custom_field"] == "value"
        assert "other_field" not in data

        # Cleanup
        logging.getLogger().removeHandler(handler)


class TestAddJsonFileHandler:
    """Tests for add_json_file_handler."""

    def test_add_json_file_handler(self, tmp_path):
        """Test adding JSON file handler."""
        cfg = Config()
        cfg.log_json = True

        log_file = tmp_path / "test.log"
        handler = add_json_file_handler(cfg, str(log_file), level=logging.INFO)

        logger = logging.getLogger("test_file")
        logger.info("File log message", extra={"request_id": "req-456"})

        # Flush and read
        handler.flush()
        content = log_file.read_text().strip()
        data = json.loads(content)

        assert data["level"] == "INFO"
        assert data["message"] == "File log message"
        assert data["request_id"] == "req-456"

        # Cleanup
        logging.getLogger().removeHandler(handler)


class TestJsonFormatterEdgeCases:
    """Edge case tests for JsonFormatter."""

    def test_timestamp_format_iso(self):
        """Test ISO timestamp format."""
        formatter = JsonFormatter(timestamp_format="iso")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.module = "test"
        record.funcName = "test"

        output = formatter.format(record)
        data = json.loads(output)

        # ISO format: YYYY-MM-DDTHH:MM:SS.mmmmmm
        assert "T" in data["timestamp"]
        assert "." in data["timestamp"]

    def test_timestamp_format_epoch(self):
        """Test epoch timestamp format."""
        formatter = JsonFormatter(timestamp_format="epoch")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.module = "test"
        record.funcName = "test"

        output = formatter.format(record)
        data = json.loads(output)

        # Epoch format: float
        assert isinstance(data["timestamp"], str)
        ts = float(data["timestamp"])
        assert ts > 1_000_000_000  # After year 2001

    def test_include_extra_false(self):
        """Test with include_extra=False."""
        formatter = JsonFormatter(include_extra=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.module = "test"
        record.funcName = "test"
        record.request_id = "req-123"

        output = formatter.format(record)
        data = json.loads(output)

        assert "request_id" not in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
