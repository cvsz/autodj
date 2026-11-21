"""Base stream adapter class.

Defines the interface all platform adapters implement. AutoDJ's chat system
treats every platform the same: inbound chat/comment messages become
ChatMessage instances, and outbound messages go through send().

Ported from cvsz/streamdbc internal/ingest bounded protocol adapters.
"""

from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field


@dataclass
class ChatMessage:
    """A single chat/comment message from a platform."""

    user: str
    text: str
    platform: str = ""  # camfrog | youtube | tiktok | facebook
    stream_id: str = ""  # safe room/stream id
    is_im: bool = False  # private/direct message
    is_admin: bool = False  # user is an admin/moderator
    timestamp: float = field(default_factory=time.time)
    raw: dict = field(default_factory=dict)  # platform-specific raw payload


class AdapterState:
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"


class AdapterError(Exception):
    """Adapter-level error (connection, auth, rate limit)."""


class StreamAdapter(ABC):
    """Base class for platform adapters.

    Subclasses must implement connect(), messages(), send(), and close().
    """

    def __init__(
        self,
        platform: str,
        stream_id: str,
        probe_account: dict | None = None,
    ) -> None:
        self.platform = platform
        self.stream_id = stream_id
        self.probe_account = probe_account or {}
        self._state: str = AdapterState.DISCONNECTED
        self._lock = threading.RLock()
        self._closed = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    @property
    def connected(self) -> bool:
        return self.state == AdapterState.CONNECTED

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    @abstractmethod
    def connect(self) -> None:
        """Authenticate with the probe account and open the channel."""
        ...

    @abstractmethod
    def messages(self) -> Iterator[ChatMessage]:
        """Yield incoming chat/comment messages.

        This is a blocking generator: it yields messages as they arrive and
        only returns when the adapter is closed or the connection dies.
        """
        ...

    @abstractmethod
    def send(self, text: str) -> None:
        """Post *text* back to the platform channel."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Cleanly disconnect and release resources."""
        ...

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _set_state(self, state: str) -> None:
        with self._lock:
            self._state = state

    def _is_closed(self) -> bool:
        return self._closed

    def _mark_closed(self) -> None:
        self._closed = True
