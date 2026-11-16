"""ระบบเพลงโปรด (Favorites) — เก็บเพลงที่ผู้ใช้ถูกใจในไฟล์ JSON.

จัดเก็บไฟล์ favorites.json ถัดจาก config.toml โดยใช้รูปแบบ:
{
  "users": {
    "nickname": [
      {"title": "เพลงที่ 1", "source": "https://youtu.be/...", "requester": "nickname", "added_at": "..."},
      ...
    ]
  }
}
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Track

log = logging.getLogger("autodj")


class FavoritesStore:
    """ร้านค้าเพลงโปรดต่อผู้ใช้ — thread-safe, เก็บเป็นไฟล์ JSON เดียว."""

    def __init__(self, cfg_path: str | None = None):
        self._lock = threading.Lock()
        if cfg_path:
            self._path = Path(cfg_path).parent / "favorites.json"
        else:
            self._path = Path("favorites.json")
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
            tmp = self._path.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps({"users": self._data}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(self._path)
        except OSError:
            log.exception("failed to save favorites file %r", self._path)

    def add(self, user: str, track: "Track") -> None:
        """เพิ่มเพลงเข้าเพลงโปรดของผู้ใช้ (กันซ้ำโดยใช้ source เป็นคีย์)."""
        key = user.lower()
        with self._lock:
            entries = self._data.setdefault(key, [])
            for entry in entries:
                if entry.get("source") == track.source:
                    return  # มีอยู่แล้ว ไม่เพิ่มซ้ำ
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
        """คืนรายการเพลงโปรดของผู้ใช้."""
        with self._lock:
            return list(self._data.get(user.lower(), []))

    def get(self, user: str, index: int) -> dict | None:
        """คืนเพลงโปรดลำดับที่ index (เริ่มที่ 1) ของผู้ใช้."""
        with self._lock:
            entries = self._data.get(user.lower(), [])
            if 1 <= index <= len(entries):
                return entries[index - 1]
            return None

    def remove(self, user: str, index: int) -> bool:
        """ลบเพลงโปรดลำดับที่ index ของผู้ใช้."""
        with self._lock:
            entries = self._data.get(user.lower(), [])
            if 1 <= index <= len(entries):
                entries.pop(index - 1)
                self._save()
                return True
            return False

    def clear(self, user: str) -> int:
        """ลบเพลงโปรดทั้งหมดของผู้ใช้ คืนจำนวนที่ลบ."""
        with self._lock:
            key = user.lower()
            count = len(self._data.pop(key, []))
            if count:
                self._save()
            return count
