"""Facebook Live comments adapter with probe account login.

Connects to Facebook Live via a probe account using the Graph API.
Polls comments on a live video post for !play requests and posts responses
back as comments.

Requires:
    pip install requests

Configuration (config.toml):
    [streams.platforms.facebook]
    enable = true
    page_id = "123456789"  # Facebook page ID running the live stream
    probe_account = {
        email = "probe@example.com",
        access_token = "EAA...",
        client_id = "....",
        client_secret = "....",
    }
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from typing import Optional

import requests

from ..probe_login import ProbeLoginError
from .base import AdapterError, AdapterState, ChatMessage, StreamAdapter

_LOG = logging.getLogger("autodj.stream")


class FacebookAdapter(StreamAdapter):
    """Facebook Live comments adapter via Graph API.

    Polls comments on a Facebook Page's live video post using a probe account's
    access token. Songs requested with !play are forwarded to AutoDJ's command
    system; bot responses are posted back as comments.
    """

    # access_token defaults to "" (none given), not a hard-coded secret
    def __init__(  # nosec B107
        self,
        stream_id: str,
        page_id: str = "",
        access_token: str = "",
        probe_account: dict | None = None,
        login_manager=None,
    ) -> None:
        super().__init__("facebook", stream_id, probe_account)
        self.page_id = page_id or self.probe_account.get("page_id", "")
        self.access_token = access_token or self.probe_account.get("access_token", "")
        self._live_video_id: Optional[str] = None
        self._comment_cursor: Optional[str] = None
        self._poll_interval = 10.0  # seconds between polls
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "AutoDJ/0.4.0 (facebook-live-adapter)"})
        self._login_manager = login_manager

    # ------------------------------------------------------------------
    # Probe account login
    # ------------------------------------------------------------------
    def login_with_probe_account(self) -> None:
        """Authenticate using the probe account's Facebook access token.

        Reads access_token from probe_account config, validates it against
        the Graph API, and refreshes if needed via the login manager.
        """
        if not self.probe_account:
            raise AdapterError("facebook probe_account not configured")

        page_id = self.probe_account.get("page_id", "")
        access_token = self.probe_account.get("access_token", "")

        if not page_id:
            raise AdapterError("facebook probe_account page_id is required")
        if not access_token:
            raise AdapterError("facebook probe_account access_token is required")

        self.page_id = self.page_id or page_id
        self.access_token = access_token

        # Try to use login manager for token validation
        if self._login_manager:
            try:
                self.access_token = self._login_manager.get_facebook_access_token(
                    self.probe_account.get("email", "facebook_probe")
                )
            except ProbeLoginError as exc:
                # Fallback to stored access token
                if not self.access_token:
                    raise AdapterError(f"facebook login failed: {exc}") from exc

        self._set_state(AdapterState.CONNECTING)
        try:
            # Validate the token by querying /me
            resp = self._session.get(
                "https://graph.facebook.com/me",
                params={"access_token": self.access_token, "fields": "id,name"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                raise AdapterError(f"facebook token invalid: {data['error']}")

            # Find active live videos on the page
            url = f"https://graph.facebook.com/v18.0/{self.page_id}/live_videos"
            params = {
                "access_token": self.access_token,
                "fields": "id,status,title",
                "filter": "live",
            }
            resp = self._session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            videos = data.get("data", [])
            if not videos:
                raise AdapterError(f"no active live video on page {self.page_id}")

            # Use the first live video
            self._live_video_id = videos[0]["id"]
            self._comment_cursor = None
            self._set_state(AdapterState.CONNECTED)
        except Exception as exc:  # noqa: BLE001
            self._set_state(AdapterState.ERROR)
            raise AdapterError(f"facebook connect failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def connect(self) -> None:
        """Authenticate and locate the active live video on the page."""
        self.login_with_probe_account()

    def messages(self) -> Iterator[ChatMessage]:
        """Poll Facebook comments on the live video for new messages."""
        if self._live_video_id is None:
            raise AdapterError("facebook adapter not connected")

        self._set_state(AdapterState.CONNECTED)
        while not self._is_closed():
            try:
                url = f"https://graph.facebook.com/v18.0/{self._live_video_id}/comments"
                params = {
                    "access_token": self.access_token,
                    "fields": "id,from{name},message,created_time",
                    "order": "chronological",
                    "limit": 100,
                }
                if self._comment_cursor:
                    params["after"] = self._comment_cursor

                resp = self._session.get(url, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                comments = data.get("data", [])
                for comment in comments:
                    message = comment.get("message", "")
                    if not message:
                        continue
                    from_info = comment.get("from", {})
                    yield ChatMessage(
                        user=from_info.get("name", "unknown"),
                        text=message,
                        platform="facebook",
                        stream_id=self.stream_id,
                        is_im=False,
                        is_admin=False,
                        timestamp=time.time(),
                        raw=comment,
                    )

                # Pagination cursor
                paging = data.get("paging", {})
                cursors = paging.get("cursors", {})
                self._comment_cursor = cursors.get("after")

                time.sleep(self._poll_interval)

            except Exception:  # noqa: BLE001 - keep polling on transient errors
                self._set_state(AdapterState.RECONNECTING)
                time.sleep(self._poll_interval)
                try:
                    self.connect()
                except Exception:  # noqa: BLE001 - retried after the next poll interval
                    _LOG.debug("Facebook reconnect failed", exc_info=True)

    def send(self, text: str) -> None:
        """Post *text* as a comment on the Facebook live video."""
        if self._live_video_id is None:
            raise AdapterError("facebook adapter not connected")
        try:
            url = f"https://graph.facebook.com/v18.0/{self._live_video_id}/comments"
            data = {
                "access_token": self.access_token,
                "message": text,
            }
            resp = self._session.post(url, data=data, timeout=15)
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            raise AdapterError(f"facebook send failed: {exc}") from exc

    def close(self) -> None:
        """Disconnect from Facebook Live."""
        self._set_state(AdapterState.DISCONNECTED)
        self._mark_closed()
        self._session.close()

    def _is_closed(self) -> bool:
        return self._closed
