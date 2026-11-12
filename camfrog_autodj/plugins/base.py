"""Plugin base interface for CamfrogAutoDJ."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from camfrog_autodj.adapters.base import ChatMessage
    from camfrog_autodj.engine import Engine
    from camfrog_autodj.models import Track


class PluginInterface:
    """Safe interface exposed to plugins - no engine internals.

    Plugins interact with the engine through this interface,
    which provides controlled access to engine functionality.
    """

    def __init__(self, engine: "Engine"):
        self._engine = engine

    def queue_track(self, query: str, user: str = "plugin") -> None:
        """Queue a track for playback."""
        self._engine.request(query, user)

    def skip_track(self) -> None:
        """Skip the currently playing track."""
        self._engine.skip()

    def set_volume(self, volume: int) -> None:
        """Set playback volume (0-100)."""
        self._engine.set_volume(volume)

    def get_status(self) -> dict:
        """Get current playback status."""
        return self._engine.snapshot()

    def say(self, text: str) -> bool:
        """Send a message to the chat room."""
        return self._engine.say(text)

    def get_config(self) -> "ConfigView":
        """Get read-only view of safe config settings."""
        return ConfigView(self._engine.cfg)


class ConfigView:
    """Read-only view of safe configuration settings for plugins."""

    def __init__(self, config):
        self._config = config
        self._safe_keys = {
            "volume",
            "max_queue",
            "max_duration",
            "shuffle",
            "repeat",
            "lang",
            "prefix",
            "bot_nick",
            "max_requests_per_user",
            "cooldown",
            "send_interval",
            "poll_interval",
            "search_limit",
            "mpv_timeout",
            "autoplay_idle_timeout",
            "auto_reply_enabled",
            "auto_reply_interval",
            "admin_greeting_enabled",
        }

    def __getattr__(self, name: str) -> Any:
        if name in self._safe_keys and hasattr(self._config, name):
            return getattr(self._config, name)
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def __dir__(self) -> list[str]:
        return sorted(self._safe_keys)


class Plugin(ABC):
    """Base class for all plugins.

    Plugins must implement on_load(). Other methods are optional.
    """

    name: str = ""
    version: str = "1.0.0"
    description: str = ""

    def __init__(self):
        self._interface: PluginInterface | None = None

    @abstractmethod
    def on_load(self, interface: PluginInterface) -> None:
        """Called when plugin is loaded.

        Args:
            interface: Safe interface for interacting with the engine.
        """
        pass

    def on_unload(self) -> None:  # noqa: B027
        """Called when plugin is unloaded. Override if needed."""
        pass

    def on_track_start(self, track: "Track") -> None:  # noqa: B027
        """Called when a track starts playing. Override if needed."""
        pass

    def on_track_end(self, track: "Track") -> None:  # noqa: B027
        """Called when a track finishes playing. Override if needed."""
        pass

    def on_command(self, command: str, user: str, args: str, is_admin: bool) -> bool:
        """Called when a command is received.

        Returns:
            True if command was handled, False otherwise.
        """
        return False

    def on_chat(self, message: "ChatMessage") -> None:  # noqa: B027
        """Called when a chat message is received. Override if needed."""
        pass

    def on_track_failed(self, track: "Track", error: str) -> None:  # noqa: B027
        """Called when a track fails to play. Override if needed."""
        pass
