"""TikTok Live chat adapter with probe account login.

Connects to TikTok Live chat via a probe account using the TikTokLive
unofficial client. Users on TikTok Live can request songs with !play and
the bot responds in chat.

Requires:
    pip install TikTokLive

Configuration (config.toml):
    [streams.platforms.tiktok]
    enable = true
    room_id = "TIKAUTODJ_PROBE_ROOM"  # TikTok Live room id (unique_id)
    probe_account = {
        username = "probe_user",
        password = "encrypted_password",
    }
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Iterator
from typing import Any, Optional

from ..probe_login import ProbeLoginError
from .base import AdapterError, AdapterState, ChatMessage, StreamAdapter

_LOG = logging.getLogger("autodj.stream")


class TikTokAdapter(StreamAdapter):
    """TikTok Live chat adapter via probe account.

    Connects to a TikTok Live room's chat websocket using a probe account.
    Monitors comments for !play requests and posts responses back.
    """

    def __init__(
        self,
        stream_id: str,
        room_id: str = "",
        probe_account: dict | None = None,
        login_manager=None,
    ) -> None:
        super().__init__("tiktok", stream_id, probe_account)
        self.room_id = room_id or self.probe_account.get("room_id", "")
        self._client: Optional[Any] = None  # TikTokLive client instance
        self._incoming: list[ChatMessage] = []
        self._incoming_lock = threading.Lock()
        self._poll_interval = 3.0
        self._login_manager = login_manager
        self._username: str = ""
        self._password: str = ""

    # ------------------------------------------------------------------
    # Probe account login
    # ------------------------------------------------------------------
    def login_with_probe_account(self) -> None:
        """Authenticate using the probe account credentials.

        Reads username/password from probe_account config. TikTokLive
        handles the actual session authentication when it connects.
        """
        if not self.probe_account:
            raise AdapterError("tiktok probe_account not configured")

        username = self.probe_account.get("username", "")
        password = self.probe_account.get("password", "")
        room_id = self.probe_account.get("room_id", "")

        if not username:
            raise AdapterError("tiktok probe_account username is required")

        if self._login_manager:
            try:
                self._username, self._password = self._login_manager.get_tiktok_credentials(
                    username
                )
            except ProbeLoginError as exc:
                # Fallback to stored credentials
                self._username = username
                self._password = password
                if not self._password:
                    raise AdapterError(f"tiktok login failed: {exc}") from exc
        else:
            self._username = username
            self._password = password

        if room_id:
            self.room_id = room_id

        if not self.room_id:
            raise AdapterError("tiktok room_id is required")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def connect(self) -> None:
        """Authenticate and connect to the TikTok Live room chat."""
        self.login_with_probe_account()

        try:
            from TikTokLive import TikTokLiveClient
        except ImportError as exc:
            raise AdapterError("TikTokLive not installed: pip install TikTokLive") from exc

        if not self.room_id:
            raise AdapterError("tiktok room_id is required")

        self._set_state(AdapterState.CONNECTING)
        try:
            client: Any = TikTokLiveClient(unique_id=self.room_id)

            # Register comment handler
            @client.on("comment")
            def _on_comment(event):
                user = event.user.nickname if event.user else "unknown"
                message = event.comment or ""
                if message:
                    with self._incoming_lock:
                        self._incoming.append(
                            ChatMessage(
                                user=user,
                                text=message,
                                platform="tiktok",
                                stream_id=self.stream_id,
                                is_im=False,
                                is_admin=False,
                                timestamp=time.time(),
                                raw={"event": "comment"},
                            )
                        )

            self._client = client
            client.run()
            self._set_state(AdapterState.CONNECTED)
        except Exception as exc:  # noqa: BLE001
            self._set_state(AdapterState.ERROR)
            raise AdapterError(f"tiktok connect failed: {exc}") from exc

    def messages(self) -> Iterator[ChatMessage]:
        """Yield incoming TikTok Live chat comments."""
        self._set_state(AdapterState.CONNECTED)
        while not self._is_closed():
            # Drain the incoming queue
            with self._incoming_lock:
                messages = list(self._incoming)
                self._incoming.clear()
            for msg in messages:
                yield msg
            time.sleep(0.5)

    def send(self, text: str) -> None:
        """Post *text* as a chat message on TikTok Live.

        TikTokLive primarily supports sending gifts/likes; chat messages
        from bots are limited. This is a best-effort placeholder.
        """
        raise AdapterError("tiktok send is not supported (TikTokLive is read-only for chat)")

    def close(self) -> None:
        """Disconnect from TikTok Live."""
        self._set_state(AdapterState.DISCONNECTED)
        self._mark_closed()
        if self._client is not None:
            try:
                self._client.stop()
            except Exception:  # noqa: BLE001 - closing must not raise
                _LOG.debug("TikTok client stop failed", exc_info=True)

    def _is_closed(self) -> bool:
        return self._closed
