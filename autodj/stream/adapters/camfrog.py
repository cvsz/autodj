"""Camfrog adapter wrapper.

Wraps AutoDJ's existing UIA chat adapter as a platform adapter so Camfrog
participates in the multi-platform stream registry with the same interface
as YouTube, TikTok, and Facebook.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any, Optional

from ..adapters.base import AdapterError, AdapterState, ChatMessage, StreamAdapter


class CamfrogAdapter(StreamAdapter):
    """Camfrog room adapter wrapping the existing UIA chat pipeline.

    Reuses AutoDJ's UIA-based chat reader/sender. The stream_id is the
    Camfrog room name (sanitized to a safe identifier).
    """

    def __init__(
        self,
        stream_id: str,
        chat_reader,
        chat_sender,
        probe_account: dict | None = None,
    ) -> None:
        super().__init__("camfrog", stream_id, probe_account)
        self._reader = chat_reader
        self._sender = chat_sender
        self._iterator: Optional[Any] = None

    def connect(self) -> None:
        """The UIA adapter is already connected via AutoDJ's engine startup."""
        self._set_state(AdapterState.CONNECTED)
        # Prime the message iterator
        try:
            self._iterator = iter(self._reader.messages())
        except Exception as exc:  # noqa: BLE001
            self._set_state(AdapterState.ERROR)
            raise AdapterError(f"camfrog connect failed: {exc}") from exc

    def messages(self) -> Iterator[ChatMessage]:
        """Yield incoming Camfrog chat lines."""
        self._set_state(AdapterState.CONNECTED)
        while not self._is_closed():
            try:
                iterator = self._iterator
                if iterator is None:
                    raise StopIteration
                msg = next(iterator)
            except StopIteration:
                # Reader exhausted; try re-priming
                try:
                    self._iterator = iter(self._reader.messages())
                except Exception:
                    break
                continue
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
                continue

            # Normalize into ChatMessage
            user = getattr(msg, "user", "unknown")
            text = getattr(msg, "text", str(msg))
            is_im = getattr(msg, "is_im", False)
            yield ChatMessage(
                user=user,
                text=text,
                platform="camfrog",
                stream_id=self.stream_id,
                is_im=is_im,
                is_admin=False,
                timestamp=time.time(),
                raw={},
            )

    def send(self, text: str) -> None:
        """Send *text* into the Camfrog room via UIA."""
        if self._sender is None:
            raise AdapterError("camfrog sender not available")
        try:
            self._sender.send(text)
        except Exception as exc:  # noqa: BLE001
            raise AdapterError(f"camfrog send failed: {exc}") from exc

    def close(self) -> None:
        """Disconnect from Camfrog chat."""
        self._set_state(AdapterState.DISCONNECTED)
        self._mark_closed()

    def _is_closed(self) -> bool:
        return self._closed
