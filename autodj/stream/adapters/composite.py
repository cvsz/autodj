"""Composite stream adapter.

Combines multiple platform adapters (Camfrog, YouTube, TikTok, Facebook) into
a single ``messages()`` iterator so AutoDJ's engine can treat all platforms
as one chat source.  Messages carry a ``platform`` field so responses can be
routed back to the right platform.

Ported from cvsz/streamdbc bounded protocol adapter pattern.
"""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Iterator

from .base import AdapterState, ChatMessage, StreamAdapter

_LOG = logging.getLogger("autodj.stream")


class CompositeStreamAdapter(StreamAdapter):
    """Combine multiple platform adapters into one chat source.

    Each adapter runs in its own thread, pushing messages into a shared
    queue.  ``messages()`` yields from that queue, so the engine sees a
    single stream of chat lines from all platforms.
    """

    def __init__(
        self,
        adapters: dict[str, StreamAdapter],
        send_callback,
    ) -> None:
        super().__init__("composite", "composite")
        self._adapters = dict(adapters)
        self._send_callback = send_callback
        self._queue: "queue.Queue[ChatMessage | None]" = queue.Queue()
        self._threads: list[threading.Thread] = []
        self._stop = threading.Event()

    # ------------------------------------------------------------------
    # StreamAdapter interface
    # ------------------------------------------------------------------
    def connect(self) -> None:
        """Connect all sub-adapters and start their message-pump threads."""
        for name, adapter in self._adapters.items():
            try:
                adapter.connect()
            except Exception:  # noqa: BLE001
                # One platform failing must not kill the others
                _LOG.exception("adapter %s connect failed", name)
                continue

        self._stop.clear()
        for name, adapter in self._adapters.items():
            t = threading.Thread(
                target=self._pump,
                args=(name, adapter),
                daemon=True,
                name=f"composite-{name}",
            )
            t.start()
            self._threads.append(t)

        self._set_state(AdapterState.CONNECTED)

    def _pump(self, platform: str, adapter: StreamAdapter) -> None:
        """Pull messages from one adapter and enqueue them."""
        try:
            for msg in adapter.messages():
                if self._stop.is_set():
                    break
                # Tag with platform if not already set
                if not msg.platform:
                    msg.platform = platform
                self._queue.put(msg)
            # Adapter ended: try to reconnect
            if not self._stop.is_set():
                try:
                    adapter.connect()
                except Exception:  # noqa: BLE001 - the reader thread must not die
                    _LOG.debug("adapter %s reconnect failed", platform, exc_info=True)
        except Exception:  # noqa: BLE001 - the reader thread must not die
            _LOG.warning("adapter %s message loop stopped", platform, exc_info=True)

    def messages(self) -> Iterator[ChatMessage]:
        """Yield chat messages from all platforms."""
        self._set_state(AdapterState.CONNECTED)
        while not self._stop.is_set():
            try:
                msg = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if msg is None:
                break
            yield msg

    def send(self, text: str) -> None:
        """Send *text* to all connected platforms."""
        for _name, adapter in self._adapters.items():
            try:
                adapter.send(text)
            except Exception:  # noqa: BLE001, S110
                # One platform failing must not block the others
                _LOG.exception("send to %s failed", _name)

    def close(self) -> None:
        """Close all sub-adapters and stop pump threads."""
        self._stop.set()
        self._queue.put(None)  # unblock messages()
        for _name, adapter in self._adapters.items():
            try:
                adapter.close()
            except Exception:  # noqa: BLE001 - closing must reach every adapter
                _LOG.debug("adapter %s close failed", _name, exc_info=True)
        for t in self._threads:
            t.join(timeout=5.0)
        self._set_state(AdapterState.DISCONNECTED)

    def _is_closed(self) -> bool:
        return self._stop.is_set()
