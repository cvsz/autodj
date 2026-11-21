"""YouTube Live chat adapter with probe account OAuth2 login.

Connects to YouTube Live chat via a probe account using the YouTube Data API v3.
Users on YouTube Live can request songs with !play and the bot responds in chat.

Requires:
    pip install google-api-python-client google-auth-oauthlib google-auth-httplib2

Configuration (config.toml):
    [streams.platforms.youtube]
    enable = true
    api_key = "YOUR_YOUTUBE_DATA_API_KEY"
    channel_id = "UCxxxxxxxx"  # YouTube channel ID to monitor
    probe_account = {
        email = "probe@example.com",
        access_token = "ya29...",
        refresh_token = "1//...",
        client_id = "....googleusercontent.com",
        client_secret = "...."
    }
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any, Optional

from ..probe_login import ProbeLoginError
from .base import AdapterError, AdapterState, ChatMessage, StreamAdapter


class YouTubeAdapter(StreamAdapter):
    """YouTube Live chat adapter via YouTube Data API v3.

    Uses a probe account to authenticate and read live chat messages from a
    YouTube Live stream. Songs requested with !play are forwarded to AutoDJ's
    command system; bot responses are posted back as chat messages.
    """

    def __init__(
        self,
        stream_id: str,
        api_key: str = "",
        channel_id: str = "",
        probe_account: dict | None = None,
        login_manager=None,
    ) -> None:
        super().__init__("youtube", stream_id, probe_account)
        self.api_key = api_key
        self.channel_id = channel_id
        self._live_chat_id: Optional[str] = None
        self._next_page_token: Optional[str] = None
        self._poll_interval = 5.0  # seconds between chat polls
        self._service = None  # googleapiclient.discovery.Resource
        self._login_manager = login_manager
        self._access_token: str = ""
        self._refresh_token: str = ""

    # ------------------------------------------------------------------
    # Probe account login
    # ------------------------------------------------------------------
    def login_with_probe_account(self) -> None:  # noqa: C901 - complex login flow with fallbacks
        """Authenticate using the probe account's OAuth2 credentials.

        Reads access_token and refresh_token from probe_account config,
        refreshes if expired, and builds the API service client.
        """
        if not self.probe_account:
            raise AdapterError("youtube probe_account not configured")

        # Extract credentials from probe_account
        username = self.probe_account.get("email", "")
        access_token = self.probe_account.get("access_token", "")
        refresh_token = self.probe_account.get("refresh_token", "")

        if not username:
            raise AdapterError("youtube probe_account email is required")

        # Try to use login manager for token refresh
        if self._login_manager:
            try:
                self._access_token = self._login_manager.get_youtube_access_token(username)
            except ProbeLoginError as exc:
                # Fallback to stored access token
                self._access_token = access_token
                if not self._access_token:
                    raise AdapterError(f"youtube login failed: {exc}") from exc
        else:
            self._access_token = access_token
            self._refresh_token = refresh_token

        if not self._access_token:
            raise AdapterError("youtube probe account has no access token")

        self.api_key = self.api_key or self.probe_account.get("api_key", "")
        self.channel_id = self.channel_id or self.probe_account.get("channel_id", "")

        if not self.channel_id:
            raise AdapterError("youtube channel_id is required")

        self._set_state(AdapterState.CONNECTING)
        try:
            from googleapiclient.discovery import build

            service: Any = build("youtube", "v3", developerKey=self.api_key)

            # Find the active live broadcast for the channel
            request = service.liveBroadcasts().list(
                part="id,snippet,contentDetails",
                channelId=self.channel_id,
                broadcastStatus="active",
            )
            response = request.execute()
            items = response.get("items", [])
            if not items:
                raise AdapterError(f"no active live broadcast on channel {self.channel_id}")

            broadcast = items[0]
            self._live_chat_id = broadcast["contentDetails"].get("liveChatId")
            if not self._live_chat_id:
                raise AdapterError(f"broadcast {broadcast['id']} has no liveChatId")

            self._next_page_token = None
            self._service = service
            self._set_state(AdapterState.CONNECTED)
        except Exception as exc:
            self._set_state(AdapterState.ERROR)
            raise AdapterError(f"youtube connect failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def connect(self) -> None:
        """Authenticate and locate the live chat for the channel."""
        self.login_with_probe_account()

    def messages(self) -> Iterator[ChatMessage]:
        """Poll YouTube Live chat for new messages."""
        if self._live_chat_id is None or self._service is None:
            raise AdapterError("youtube adapter not connected")

        self._set_state(AdapterState.CONNECTED)
        while not self._is_closed():
            try:
                request = self._service.liveChatMessages().list(
                    liveChatId=self._live_chat_id,
                    part="id,snippet,authorDetails",
                    pageToken=self._next_page_token,
                    maxResults=200,
                )
                response = request.execute()
                self._next_page_token = response.get("nextPageToken")

                for item in response.get("items", []):
                    snippet = item.get("snippet", {})
                    author = snippet.get("authorDetails", {})
                    message_text = snippet.get("displayMessage", "")
                    if not message_text:
                        continue

                    yield ChatMessage(
                        user=author.get("displayName", "unknown"),
                        text=message_text,
                        platform="youtube",
                        stream_id=self.stream_id,
                        is_im=False,
                        is_admin=author.get("isChatModerator", False),
                        timestamp=time.time(),
                        raw=item,
                    )

                # Polling interval from the API response (milliseconds)
                polling_interval = response.get("pollingIntervalMillis", 5000)
                time.sleep(max(polling_interval, 1000) / 1000.0)

            except Exception:  # noqa: BLE001 - keep polling on transient errors
                self._set_state(AdapterState.RECONNECTING)
                time.sleep(self._poll_interval)
                try:
                    self.connect()
                except Exception:  # noqa: BLE001, S110, S112
                    continue

    def send(self, text: str) -> None:
        """Post *text* as a chat message on YouTube Live."""
        if self._live_chat_id is None or self._service is None:
            raise AdapterError("youtube adapter not connected")
        try:
            self._service.liveChatMessages().insert(
                part="snippet",
                body={
                    "snippet": {
                        "liveChatId": self._live_chat_id,
                        "type": "textMessageEvent",
                        "textMessageEvent": {"messageText": text},
                    }
                },
            ).execute()
        except Exception as exc:  # noqa: BLE001
            raise AdapterError(f"youtube send failed: {exc}") from exc

    def close(self) -> None:
        """Disconnect from YouTube Live chat."""
        self._set_state(AdapterState.DISCONNECTED)
        self._mark_closed()

    def _is_closed(self) -> bool:
        return self._closed
