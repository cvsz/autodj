"""Built-in stats plugin: tracks play statistics and provides a !stats command."""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path

from ..base import Plugin

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
        super().on_load(interface)
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
            self.interface.say(msg)
            return True
        return False
