"""Built-in plugins for CamfrogAutoDJ."""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path

from .base import Plugin

log = logging.getLogger("autodj.plugins.stats")


class StatsPlugin(Plugin):
    """Track play statistics, top users, top tracks."""

    name = "stats"
    version = "1.0.0"
    description = "Track play statistics and provide stats command"

    def __init__(self):
        super().__init__()
        self.stats_file = Path("plugin_stats.json")
        self.track_counts: Counter[str] = Counter()
        self.user_counts: Counter[str] = Counter()
        self.total_plays = 0
        self._load()

    def _load(self) -> None:
        if self.stats_file.exists():
            try:
                data = json.loads(self.stats_file.read_text())
                self.track_counts = Counter(data.get("tracks", {}))
                self.user_counts = Counter(data.get("users", {}))
                self.total_plays = data.get("total_plays", 0)
            except Exception:
                log.exception("Failed to load stats")

    def _save(self) -> None:
        try:
            data = {
                "tracks": dict(self.track_counts),
                "users": dict(self.user_counts),
                "total_plays": self.total_plays,
            }
            self.stats_file.write_text(json.dumps(data))
        except Exception:
            log.exception("Failed to save stats")

    def on_load(self, interface) -> None:
        log.info("Stats plugin loaded")

    def on_unload(self) -> None:
        self._save()
        log.info("Stats plugin unloaded")

    def on_track_start(self, track) -> None:
        title = getattr(track, "title", str(track))
        requester = getattr(track, "requester", "Unknown")
        self.track_counts[title] += 1
        self.user_counts[requester] += 1
        self.total_plays += 1
        self._save()

    def on_command(self, command: str, user: str, args: str, is_admin: bool) -> bool:
        if command.lower() in ("stats", "statistics", "สถิติ"):
            top_tracks = self.track_counts.most_common(5)
            top_users = self.user_counts.most_common(5)
            msg = (
                f"📊 Top tracks: {', '.join(f'{t} ({c})' for t, c in top_tracks) or 'none'} | "
                f"Top users: {', '.join(f'{u} ({c})' for u, c in top_users) or 'none'} | "
                f"Total plays: {self.total_plays}"
            )
            self._interface.say(msg)
            return True
        return False


class HelpPlugin(Plugin):
    """Provides extended help information."""

    name = "help"
    version = "1.0.0"
    description = "Extended help command with plugin information"

    def __init__(self):
        super().__init__()
        self._plugin_manager = None

    def on_load(self, interface) -> None:
        # Store reference to plugin manager via interface
        self._interface = interface
        log.info("Help plugin loaded")

    def on_command(self, command: str, user: str, args: str, is_admin: bool) -> bool:
        if command.lower() in ("help", "plugins", "ช่วยเหลือ"):
            # Get plugin list from engine
            plugins = []
            if hasattr(self._interface, "_engine") and hasattr(
                self._interface._engine, "plugin_manager"
            ):
                plugins = self._interface._engine.plugin_manager.list_plugins()

            if plugins:
                plugin_list = ", ".join(f"{p['name']} v{p['version']}" for p in plugins)
                msg = f"📦 Loaded plugins: {plugin_list}"
            else:
                msg = "📦 No plugins loaded"
            self._interface.say(msg)
            return True
        return False


# Plugin registry for builtin plugins
BUILTIN_PLUGINS = {
    "stats": StatsPlugin,
    "help": HelpPlugin,
}


def get_builtin_plugin(name: str) -> type[Plugin] | None:
    """Get a builtin plugin class by name."""
    return BUILTIN_PLUGINS.get(name)
