"""Multi-platform adapter manager with probe account login.

Creates, connects, and manages stream adapters for all configured platforms
(Camfrog, YouTube, TikTok, Facebook). Routes incoming chat messages through
AutoDJ's command router and posts responses back to the originating platform.

Probe accounts are used to authenticate with each social platform. Credentials
are stored encrypted and can be rotated without restarting.

Ported patterns from cvsz/streamdbc (Go) - bounded protocol adapters with
stream-scoped auth - adapted to Python.
"""

from __future__ import annotations

import threading
import time
from typing import Optional

from ..config import Config
from .adapters.base import ChatMessage, StreamAdapter
from .adapters.camfrog import CamfrogAdapter
from .adapters.facebook import FacebookAdapter
from .adapters.tiktok import TikTokAdapter
from .adapters.youtube import YouTubeAdapter
from .auth import AuthManager, authorize
from .probe_account import ProbeAccountStore
from .probe_login import ProbeLoginManager
from .registry import StreamInfo, StreamRegistry, StreamState

_LOG = None  # placeholder for injected logging


class AdapterManager:
    """Manages all platform adapters and routes messages to AutoDJ commands.

    Each configured platform gets an adapter instance. Inbound messages are
    dispatched to a callback (AutoDJ's command router). Outbound responses
    are posted back to the originating platform.

    Probe accounts are loaded from an encrypted store and used to authenticate
    with each platform.
    """

    def __init__(
        self,
        config: Config,
        registry: StreamRegistry,
        command_callback,
        auth_manager: Optional[AuthManager] = None,
        probe_store: Optional[ProbeAccountStore] = None,
        login_manager: Optional[ProbeLoginManager] = None,
    ) -> None:
        self.config = config
        self.registry = registry
        self.command_callback = command_callback
        self.auth_manager = auth_manager
        self.probe_store = probe_store
        self.login_manager = (
            login_manager or ProbeLoginManager(probe_store) if probe_store else None
        )
        self._adapters: dict[str, StreamAdapter] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self._adapter_factories = {
            "camfrog": self._make_camfrog,
            "youtube": self._make_youtube,
            "tiktok": self._make_tiktok,
            "facebook": self._make_facebook,
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Connect all enabled platform adapters and start message loops."""
        streams_cfg = self.config.streams or {}
        if not streams_cfg.get("enabled", False):
            return

        platforms_cfg = streams_cfg.get("platforms", {})
        for platform_name, platform_cfg in platforms_cfg.items():
            if not isinstance(platform_cfg, dict):
                continue
            if not platform_cfg.get("enable", False):
                continue

            stream_id = platform_name  # safe id from config validation
            # Register stream in the stream registry
            try:
                self.registry.register(stream_id, name=platform_name)
                self.registry.set_state(stream_id, StreamState.IDLE)
            except Exception:  # noqa: BLE001, S110
                # Stream may already exist; set state to IDLE
                try:
                    self.registry.set_state(stream_id, StreamState.IDLE)
                except Exception:  # noqa: BLE001, S110
                    pass

            # Create adapter
            adapter = self._create_adapter(platform_name, platform_cfg, stream_id)
            if adapter is None:
                continue

            try:
                adapter.connect()
                self.registry.set_state(stream_id, StreamState.LIVE)
            except Exception as exc:  # noqa: BLE001, S110
                self.registry.set_state(stream_id, StreamState.ERROR)
                if _LOG:
                    _LOG.exception("adapter %s connect failed: %s", platform_name, exc)
                continue

            with self._lock:
                self._adapters[platform_name] = adapter

            # Start message loop thread
            thread = threading.Thread(
                target=self._message_loop,
                args=(platform_name, adapter),
                daemon=True,
                name=f"adapter-{platform_name}",
            )
            thread.start()
            with self._lock:
                self._threads[platform_name] = thread

    def stop(self) -> None:
        """Stop all adapters and message loops."""
        self._stop_event.set()
        with self._lock:
            adapters = dict(self._adapters)
            threads = dict(self._threads)
            self._adapters.clear()
            self._threads.clear()

        for platform_name, adapter in adapters.items():
            try:
                adapter.close()
            except Exception:  # noqa: BLE001, S110
                pass
            try:
                self.registry.set_state(platform_name, StreamState.IDLE)
            except Exception:  # noqa: BLE001, S110
                pass

        for _platform_name, thread in threads.items():
            thread.join(timeout=5.0)

    # ------------------------------------------------------------------
    # Adapter creation
    # ------------------------------------------------------------------
    def _create_adapter(
        self,
        platform_name: str,
        platform_cfg: dict,
        stream_id: str,
    ) -> Optional[StreamAdapter]:
        probe_account = platform_cfg.get("probe_account", {}) or {}
        factory = self._adapter_factories.get(platform_name)
        if factory is None:
            if _LOG:
                _LOG.warning("unknown platform %r", platform_name)
            return None
        return factory(platform_cfg, stream_id, probe_account)

    def _make_camfrog(
        self, platform_cfg: dict, stream_id: str, probe_account: dict
    ) -> Optional[StreamAdapter]:
        chat_reader = getattr(self.config, "_ui_reader", None)
        chat_sender = getattr(self.config, "_ui_sender", None)
        if chat_reader is None or chat_sender is None:
            if _LOG:
                _LOG.warning("camfrog adapter skipped: UIA reader/sender not configured")
            return None
        return CamfrogAdapter(stream_id, chat_reader, chat_sender, probe_account)

    def _make_youtube(
        self, platform_cfg: dict, stream_id: str, probe_account: dict
    ) -> Optional[StreamAdapter]:
        api_key = platform_cfg.get("api_key", "")
        channel_id = platform_cfg.get("channel_id", "")
        if not api_key and not probe_account.get("api_key"):
            if _LOG:
                _LOG.warning("youtube adapter skipped: api_key missing")
            return None
        if not channel_id and not probe_account.get("channel_id"):
            if _LOG:
                _LOG.warning("youtube adapter skipped: channel_id missing")
            return None
        return YouTubeAdapter(
            stream_id,
            api_key=api_key,
            channel_id=channel_id,
            probe_account=probe_account,
            login_manager=self.login_manager,
        )

    def _make_tiktok(
        self, platform_cfg: dict, stream_id: str, probe_account: dict
    ) -> Optional[StreamAdapter]:
        room_id = platform_cfg.get("room_id", "") or probe_account.get("room_id", "")
        if not room_id:
            if _LOG:
                _LOG.warning("tiktok adapter skipped: room_id missing")
            return None
        return TikTokAdapter(
            stream_id,
            room_id=room_id,
            probe_account=probe_account,
            login_manager=self.login_manager,
        )

    def _make_facebook(
        self, platform_cfg: dict, stream_id: str, probe_account: dict
    ) -> Optional[StreamAdapter]:
        access_token = platform_cfg.get("api_key", "") or probe_account.get("access_token", "")
        page_id = platform_cfg.get("page_id", "") or probe_account.get("page_id", "")
        if not access_token:
            if _LOG:
                _LOG.warning("facebook adapter skipped: access_token missing")
            return None
        if not page_id:
            if _LOG:
                _LOG.warning("facebook adapter skipped: page_id missing")
            return None
        return FacebookAdapter(
            stream_id,
            page_id=page_id,
            access_token=access_token,
            probe_account=probe_account,
            login_manager=self.login_manager,
        )

    # ------------------------------------------------------------------
    # Message loop
    # ------------------------------------------------------------------
    def _message_loop(self, platform_name: str, adapter: StreamAdapter) -> None:
        """Pump messages from one adapter to the command router."""
        while not self._stop_event.is_set():
            try:
                for msg in adapter.messages():
                    if self._stop_event.is_set():
                        break
                    self._dispatch_message(platform_name, msg)
            except Exception:  # noqa: BLE001, S110
                if _LOG:
                    _LOG.exception("adapter %s message loop error", platform_name)
                time.sleep(2.0)
                try:
                    adapter.connect()
                except Exception:  # noqa: BLE001, S110
                    pass

    def _dispatch_message(self, platform_name: str, msg: ChatMessage) -> None:
        """Route an inbound message through auth + command router."""
        stream_id = msg.stream_id or platform_name

        # Auth check for commands (messages starting with the prefix)
        prefix = self.config.prefix or "!"
        if msg.text.startswith(prefix):
            if self.auth_manager is not None:
                # Extract a token from the message if present: "!play song token=xxx"
                token = self._extract_token(msg.text)
                ip = getattr(msg, "raw", {}).get("ip", "")
                if not authorize(self.auth_manager, token, "publish", stream_id, ip):
                    adapter = self._adapters.get(platform_name)
                    if adapter is not None:
                        try:
                            adapter.send("❌ Not authorized to request songs on this stream.")
                        except Exception:  # noqa: BLE001, S110
                            pass
                    return

        # Forward to AutoDJ's command router
        try:
            self.command_callback(msg)
        except Exception:  # noqa: BLE001, S110
            if _LOG:
                _LOG.exception("command callback failed for %r", msg.text)

    @staticmethod
    def _extract_token(text: str) -> str:
        """Extract an optional token=xxx from a message."""
        for part in text.split():
            if part.startswith("token="):
                return part[len("token=") :]
        return ""

    # ------------------------------------------------------------------
    # Outbound
    # ------------------------------------------------------------------
    def send_to_platform(self, platform_name: str, text: str) -> None:
        """Post *text* back to the originating platform."""
        with self._lock:
            adapter = self._adapters.get(platform_name)
        if adapter is None:
            return
        try:
            adapter.send(text)
        except Exception:  # noqa: BLE001, S110
            if _LOG:
                _LOG.exception("send to %s failed", platform_name)

    def list_adapters(self) -> dict[str, str]:
        """Return {platform: state} for all connected adapters."""
        with self._lock:
            return {name: adapter.state for name, adapter in self._adapters.items()}

    def get_stream_info(self, stream_id: str) -> Optional[StreamInfo]:
        """Return stream registry info for *stream_id*."""
        return self.registry.get(stream_id)

    # ------------------------------------------------------------------
    # Probe account management
    # ------------------------------------------------------------------
    def get_probe_account(self, platform: str, username: str):
        """Get a probe account by platform and username."""
        if self.probe_store:
            return self.probe_store.get(platform, username)
        return None

    def add_probe_account(self, account) -> None:
        """Add or update a probe account."""
        if self.probe_store:
            self.probe_store.add(account)

    def list_probe_accounts(self, platform: str | None = None):
        """List probe accounts, optionally filtered by platform."""
        if self.probe_store:
            if platform:
                return self.probe_store.get_by_platform(platform)
            return self.probe_store.list_all()
        return []

    def get_active_probe_account(self, platform: str):
        """Get the first active, non-locked account for a platform."""
        if self.probe_store:
            return self.probe_store.get_active_account(platform)
        return None
