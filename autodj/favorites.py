"""User favorites system — stores tracks users like in a JSON file.

The favorites.json file lives next to config.toml and uses this format:
{
  "users": {
    "nickname": [
      {"title": "Song 1", "source": "https://youtu.be/...", "requester": "nickname", "added_at": "..."},
      ...
    ]
  }
}
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Track

log = logging.getLogger("autodj")

# One lock per favorites file, shared by every FavoritesStore instance.  Commands
# create a new store per call, so a per-instance lock (plus a snapshot loaded at
# construction) let concurrent saves overwrite each other and lose entries.
_PATH_LOCKS: dict[str, threading.Lock] = {}
_REGISTRY_LOCK = threading.Lock()


def _lock_for(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _REGISTRY_LOCK:
        return _PATH_LOCKS.setdefault(key, threading.Lock())


class FavoritesStore:
    """Per-user favorites store — thread-safe, single JSON file.

    Every operation re-reads the file under a process-wide per-file lock, so
    instances never work from a stale snapshot.
    """

    def __init__(self, cfg_path: str | None = None):
        if cfg_path:
            self._path = Path(cfg_path).parent / "favorites.json"
        else:
            self._path = Path("favorites.json")
        self._lock = _lock_for(self._path)
        with self._lock:
            self._data: dict[str, list[dict]] = self._load()

    def _load(self) -> dict[str, list[dict]]:
        try:
            text = self._path.read_text(encoding="utf-8-sig")
            data = json.loads(text)
            if isinstance(data, dict) and isinstance(data.get("users"), dict):
                return data["users"]
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, OSError):
            log.exception("failed to load favorites file %r", self._path)
        return {}

    def _save(self) -> None:
        try:
            # unique temp name: two writers must never share one .tmp file
            tmp = self._path.with_name(
                f".{self._path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
            )
            tmp.write_text(
                json.dumps({"users": self._data}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(self._path)
        except OSError:
            log.exception("failed to save favorites file %r", self._path)

    def add(self, user: str, track: "Track") -> None:
        """Add a track to a user's favorites (dedup by source)."""
        key = user.lower()
        with self._lock:
            self._data = self._load()  # fresh copy: other instances may have saved
            entries = self._data.setdefault(key, [])
            for entry in entries:
                if entry.get("source") == track.source:
                    return  # already present, do not add again
            entries.append(
                {
                    "title": track.title,
                    "source": track.source,
                    "requester": track.requester,
                    "added_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
            self._save()

    def list_for(self, user: str) -> list[dict]:
        """Return a user's favorite tracks."""
        with self._lock:
            self._data = self._load()  # fresh copy: other instances may have saved
            return list(self._data.get(user.lower(), []))

    def get(self, user: str, index: int) -> dict | None:
        """Return the user's favorite track at *index* (1-based)."""
        with self._lock:
            self._data = self._load()  # fresh copy: other instances may have saved
            entries = self._data.get(user.lower(), [])
            if 1 <= index <= len(entries):
                return entries[index - 1]
            return None

    def remove(self, user: str, index: int) -> bool:
        """Remove the user's favorite track at *index* (1-based)."""
        with self._lock:
            self._data = self._load()  # fresh copy: other instances may have saved
            entries = self._data.get(user.lower(), [])
            if 1 <= index <= len(entries):
                entries.pop(index - 1)
                self._save()
                return True
            return False

    def clear(self, user: str) -> int:
        """Remove all of a user's favorite tracks; return the number removed."""
        with self._lock:
            self._data = self._load()  # fresh copy: other instances may have saved
            key = user.lower()
            count = len(self._data.pop(key, []))
            if count:
                self._save()
            return count
