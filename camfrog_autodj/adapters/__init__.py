from __future__ import annotations

import logging
import threading
import time
from enum import Enum
from typing import Optional

from .base import ChatAdapter, ChatMessage

log = logging.getLogger(__name__)

__all__ = [
    "ChatAdapter",
    "ChatMessage",
    "Composite",
    "NullAdapter",
    "build_adapter",
    "build_adapter_with_fallback",
    "AdapterType",
    "AdapterStatus",
]


class AdapterType(Enum):
    """Supported chat adapter types in priority order (highest first)."""

    UIA = "uia"
    LOGTAIL = "logtail"
    CONSOLE = "console"
    NULL = "null"


class AdapterStatus:
    """Track adapter health and fallback state."""

    def __init__(self):
        self._lock = threading.Lock()
        self._active_adapter: str = "null"
        self._fallback_count = 0
        self._last_fallback_time: float = 0.0
        self._adapter_errors: dict[str, int] = {}
        self._last_error: str | None = None

    @property
    def active_adapter(self) -> str:
        with self._lock:
            return self._active_adapter

    @property
    def fallback_count(self) -> int:
        with self._lock:
            return self._fallback_count

    @property
    def last_fallback_time(self) -> float:
        with self._lock:
            return self._last_fallback_time

    @property
    def last_error(self) -> str | None:
        with self._lock:
            return self._last_error

    def record_fallback(self, from_adapter: str, to_adapter: str, error: str) -> None:
        with self._lock:
            self._active_adapter = to_adapter
            self._fallback_count += 1
            self._last_fallback_time = time.monotonic()
            self._adapter_errors[from_adapter] = self._adapter_errors.get(from_adapter, 0) + 1
            self._last_error = f"{from_adapter} -> {to_adapter}: {error}"
            log.warning(
                "Chat adapter fallback: %s -> %s (error: %s, total fallbacks: %d)",
                from_adapter,
                to_adapter,
                error,
                self._fallback_count,
            )

    def record_success(self, adapter: str) -> None:
        with self._lock:
            self._active_adapter = adapter
            self._last_error = None

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "active_adapter": self._active_adapter,
                "fallback_count": self._fallback_count,
                "last_fallback_time": self._last_fallback_time,
                "adapter_errors": dict(self._adapter_errors),
                "last_error": self._last_error,
            }


# Global adapter status for health check
_adapter_status = AdapterStatus()


def get_adapter_status() -> AdapterStatus:
    """Get the global adapter status tracker."""
    return _adapter_status


class Composite(ChatAdapter):
    def __init__(self, reader: ChatAdapter, sender: ChatAdapter):
        self.reader, self.sender = reader, sender

    def messages(self):
        return self.reader.messages()

    def send(self, text):
        self.sender.send(text)

    def close(self):
        self.reader.close()
        if self.sender is not self.reader:
            self.sender.close()


def _make(kind: str, cfg) -> ChatAdapter:
    if kind == "console":
        from .console import ConsoleAdapter

        return ConsoleAdapter(cfg)
    if kind == "logtail":
        from .logtail import LogTailAdapter

        return LogTailAdapter(cfg)
    if kind == "uia":
        from .uia import UiaAdapter

        return UiaAdapter(cfg)
    if kind == "null":
        return NullAdapter()
    raise ValueError(f"unknown chat adapter: {kind}")


def build_adapter_with_fallback(cfg, *, use_fallback: bool = True) -> ChatAdapter:
    """Build chat adapter with automatic fallback chain.

    Fallback chain: uia -> logtail -> console -> null

    Args:
        cfg: Config object
        use_fallback: Whether to enable fallback chain (default True)

    Returns:
        Composite adapter with reader and sender
    """
    if not use_fallback:
        # Original behavior - no fallback
        reader = _make(cfg.chat_reader, cfg)
        sender = reader if cfg.chat_sender == cfg.chat_reader else _make(cfg.chat_sender, cfg)
        _adapter_status.record_success(cfg.chat_reader)
        return Composite(reader, sender)

    # Build fallback chain for reader
    reader_kind = cfg.chat_reader
    sender_kind = cfg.chat_sender

    # Determine fallback chain based on configured reader
    fallback_chain = _get_fallback_chain(reader_kind)

    reader_adapter: Optional[ChatAdapter] = None
    last_error = None
    for i, kind in enumerate(fallback_chain):
        try:
            reader_adapter = _make(kind, cfg)
            # Test the reader by trying to get one message (with timeout)
            # This will raise if the adapter can't connect
            _test_adapter(reader_adapter)
            if i > 0:
                _adapter_status.record_fallback(
                    fallback_chain[0], kind, f"fallback after {i} attempts"
                )
            else:
                _adapter_status.record_success(kind)
            break
        except Exception as e:
            last_error = str(e)
            log.warning("Adapter %s failed: %s, trying next fallback", kind, e)
            continue

    if reader_adapter is None:
        # All fallbacks failed, use NullAdapter
        log.error("All chat adapters failed, using NullAdapter: %s", last_error)
        reader_adapter = NullAdapter()
        _adapter_status.record_fallback(
            fallback_chain[0] if fallback_chain else "unknown",
            "null",
            last_error or "all adapters failed",
        )

    # Build sender (same logic, but can be different kind)
    if sender_kind == reader_kind:
        sender_adapter = reader_adapter
    else:
        sender_fallback_chain = _get_fallback_chain(sender_kind)
        sender_adapter = None
        for kind in sender_fallback_chain:
            try:
                sender_adapter = _make(kind, cfg)
                _test_adapter(sender_adapter)
                break
            except Exception as e:
                log.warning("Sender adapter %s failed: %s, trying next", kind, e)
                continue
        if sender_adapter is None:
            sender_adapter = NullAdapter()
    assert sender_adapter is not None

    return Composite(reader_adapter, sender_adapter)


def _get_fallback_chain(primary: str) -> list[str]:
    """Get fallback chain for a primary adapter kind."""
    # Full chain in priority order
    full_chain = ["uia", "logtail", "console", "null"]
    try:
        idx = full_chain.index(primary)
        return full_chain[idx:]
    except ValueError:
        return full_chain


def _test_adapter(adapter: ChatAdapter) -> None:
    """Test if an adapter can connect by attempting to read one message.

    This is a quick test that should fail fast if the adapter can't connect.
    """
    # For UIA, this will try to resolve the window
    # For logtail, it will try to open the log file
    # For console, it always works
    # For NullAdapter, it always works
    if hasattr(adapter, "test_connection"):
        adapter.test_connection()
    elif hasattr(adapter, "resolve"):
        # UIA adapter has resolve method
        adapter.resolve()


def build_adapter(cfg) -> ChatAdapter:
    """Build adapter from config with fallback chain enabled."""
    return build_adapter_with_fallback(cfg, use_fallback=True)


class NullAdapter(ChatAdapter):
    """Fallback adapter when Camfrog cannot be reached (pywinauto missing, no room
    window open, ...). The GUI still opens; chat simply does nothing until Camfrog
    is available and discovery is re-run."""

    def messages(self):  # no chat lines ever
        return iter(())

    def send(self, text: str) -> None:
        # Deliberately do nothing: Camfrog is not reachable. Log a clear warning
        # so operators know messages are being dropped, not silently swallowed.
        log.warning(
            "Cannot send chat: Camfrog is not reachable (using NullAdapter). Message dropped: %r",
            text[:80],
        )

    def close(self) -> None:
        pass
