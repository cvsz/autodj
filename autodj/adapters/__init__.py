from __future__ import annotations

import logging
import threading
import time
from enum import Enum
from typing import TYPE_CHECKING, Callable, Iterator, Optional

from .base import ChatAdapter, ChatMessage

if TYPE_CHECKING:
    from .config import Config

log = logging.getLogger(__name__)

__all__ = [
    "ChatAdapter",
    "ChatMessage",
    "Composite",
    "NullAdapter",
    "ReattachingAdapter",
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

    def messages(self) -> Iterator[ChatMessage]:
        return self.reader.messages()

    def send(self, text: str) -> None:
        self.sender.send(text)

    @property
    def delivers(self) -> bool:
        """False when the sender only discards messages (NullAdapter)."""
        return bool(getattr(self.sender, "delivers", True))

    @property
    def room_ready(self) -> bool:
        """False while the sender cannot reach the room chat (room page not shown)."""
        return bool(getattr(self.sender, "room_ready", True))

    @property
    def send_im(self) -> Callable[[str, str], None] | None:
        """Private-message sender of the wrapped adapters, or None.

        The reader is asked first: with UIA it is the one that has seen the IM
        windows (and knows which window belongs to which user).  Without this,
        Engine.send_im found no ``send_im`` on the Composite and every IM reply
        was silently skipped in the live room.
        """
        for adapter in (self.reader, self.sender):
            fn = getattr(adapter, "send_im", None)
            if callable(fn):
                return fn  # type: ignore[no-any-return]
        return None

    def close(self) -> None:
        self.reader.close()
        if self.sender is not self.reader:
            self.sender.close()


def _make(kind: str, cfg: "Config") -> ChatAdapter:
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


def build_adapter_with_fallback(cfg: "Config", *, use_fallback: bool = True) -> ChatAdapter:
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
        sender_adapter = _first_working_sender(sender_fallback_chain, cfg)

    return Composite(reader_adapter, sender_adapter)


def _first_working_sender(chain: list[str], cfg: "Config") -> ChatAdapter:
    """First sender in *chain* that builds and passes its self-test, else NullAdapter.

    A candidate that is created but fails ``_test_adapter`` is discarded (it used
    to be kept as the sender when every candidate failed).
    """
    for kind in chain:
        try:
            cand = _make(kind, cfg)
            _test_adapter(cand)
            return cand
        except Exception as e:
            log.warning("Sender adapter %s failed: %s, trying next", kind, e)
    return NullAdapter()


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


def build_adapter(cfg: "Config") -> ChatAdapter:
    reader = _make(cfg.chat_reader, cfg)
    sender = reader if cfg.chat_sender == cfg.chat_reader else _make(cfg.chat_sender, cfg)
    return Composite(reader, sender)


class ReattachingAdapter(ChatAdapter):
    """Camfrog was not reachable at startup: keep trying instead of giving up.

    The GUI used to fall back to a NullAdapter for the whole session, so a bot
    started before the room window was open never read chat or answered IMs
    until it was restarted.  This wrapper retries ``build`` every *interval*
    seconds (and on each send) and delegates to the real adapter once the room
    window appears.
    """

    def __init__(
        self,
        cfg: "Config",
        build: "Callable[[Config], ChatAdapter] | None" = None,
        interval: float = 15.0,
    ):
        self.cfg = cfg
        self._build = build or build_adapter
        self.interval = interval
        self._inner: ChatAdapter | None = None
        self._next_try = 0.0
        self._lock = threading.Lock()
        self._closed = threading.Event()

    def _attached(self) -> ChatAdapter | None:
        """The real adapter, attaching first if a retry is due."""
        with self._lock:
            if self._inner is not None or self._closed.is_set():
                return self._inner
            now = time.monotonic()
            if now < self._next_try:
                return None
            try:
                self._inner = self._build(self.cfg)
            except Exception as ex:  # room window still closed, COM not ready, ...
                self._next_try = now + self.interval
                log.debug("Camfrog chat still not reachable: %s", ex)
                return None
            log.info("attached to Camfrog chat (the room window is open now)")
            return self._inner

    def messages(self) -> Iterator[ChatMessage]:
        while not self._closed.is_set():
            inner = self._attached()
            if inner is not None:
                yield from inner.messages()
                return
            self._closed.wait(min(self.interval, 1.0))

    def send(self, text: str) -> None:
        inner = self._attached()
        if inner is None:
            log.warning(
                "Cannot send chat: Camfrog room window is not open yet. Message dropped: %r",
                text[:80],
            )
            return
        inner.send(text)

    @property
    def delivers(self) -> bool:
        inner = self._inner
        return inner is not None and bool(getattr(inner, "delivers", True))

    @property
    def room_ready(self) -> bool:
        """True once attached and the room chat is shown (not the room list)."""
        inner = self._inner
        return inner is not None and bool(getattr(inner, "room_ready", True))

    @property
    def send_im(self) -> Callable[[str, str], None] | None:
        inner = self._attached()
        fn = getattr(inner, "send_im", None) if inner is not None else None
        return fn if callable(fn) else None

    def close(self) -> None:
        self._closed.set()
        with self._lock:
            inner, self._inner = self._inner, None
        if inner is not None:
            inner.close()


class NullAdapter(ChatAdapter):
    """Fallback adapter when Camfrog cannot be reached (pywinauto missing, no room
    window open, ...). The GUI still opens; chat simply does nothing until Camfrog
    is available and discovery is re-run."""

    delivers = False  # send() discards: the engine must not log it as delivered

    def messages(self) -> Iterator[ChatMessage]:  # no chat lines ever
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
