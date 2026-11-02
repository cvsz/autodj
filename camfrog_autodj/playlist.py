"""Persistent autoplay playlist (playlist.json).

The file is plain JSON the operator can edit by hand:
    {"version": 1, "tracks": [
        {"source": "https://www.youtube.com/watch?v=...", "title": "...", "duration": 245.0,
         "added_by": "Seaza", "added": "2026-10-28T15:10:00"},
        ...]}

* added at startup to the autoplay pool (requests still play first, then random from the pool, looping)
* every user request (and admin !load) appends its tracks here -- deduplicated by `source`
* missing or corrupt file = empty list, never fatal.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import threading
from datetime import datetime
from pathlib import Path

from .models import Track

log = logging.getLogger("autodj")

# Valid source: http(s):// URL or yt-dlp search query (ytsearchN:...)
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_SEARCH_RE = re.compile(r"^ytsearch\d+:", re.IGNORECASE)


def _is_valid_source(source: str) -> bool:
    """Return True if source is a valid URL, yt-dlp search query, or local file path."""
    if not source or not isinstance(source, str):
        return False
    s = source.strip()
    if not s:
        return False
    if _URL_RE.match(s) or _SEARCH_RE.match(s):
        return True
    # Local file path: contains path separator, starts with '.', or has a file extension
    return "/" in s or "\\" in s or s.startswith(".") or bool(Path(s).suffix)


def load_playlist(path: str) -> list[Track]:
    """Read playlist.json -> tracks; missing or broken file = [] (logged, never fatal)."""
    try:
        data = json.loads(Path(path).read_text("utf-8-sig"))
    except FileNotFoundError:
        return []
    except Exception:
        log.warning(
            "cannot read playlist file %r -- starting without it (the file will not be overwritten)",
            path,
            exc_info=True,
        )
        return []
    entries = data.get("tracks", []) if isinstance(data, dict) else data
    out = []
    for e in entries if isinstance(entries, list) else []:
        try:
            src = str(e.get("source") or "").strip()
            if not src:
                continue
            if not _is_valid_source(src):
                log.warning(
                    "playlist %r: skipping track with invalid source %r (must be http(s) URL or ytsearchN: query)",
                    path,
                    src,
                )
                continue
            dur = e.get("duration")
            t = Track(
                src,
                str(e.get("title") or src),
                dur if isinstance(dur, (int, float)) else None,
                str(e.get("added_by") or "AutoDJ"),
            )
            t.added = str(
                e.get("added") or ""
            )  # not a Track field: plain attribute, kept for !last
            out.append(t)
        except Exception:
            continue
    return out


def _unreadable(path: str) -> bool:
    """The file exists but is not usable JSON (as opposed to missing or merely empty of tracks)."""
    try:
        json.loads(Path(path).read_text("utf-8-sig"))
        return False
    except FileNotFoundError:
        return False
    except Exception:
        return True


def save_playlist(path: str, tracks: list[Track]) -> None:
    """Write the whole playlist atomically (tmp file + replace)."""
    entries = [
        {
            "source": t.source,
            "title": t.title,
            "duration": t.duration,
            "added_by": t.requester,
            "added": getattr(t, "added", ""),
        }
        for t in tracks
    ]
    tmp = path + ".tmp"
    Path(tmp).write_text(
        json.dumps({"version": 1, "tracks": entries}, ensure_ascii=False, indent=1),
        "utf-8",
    )
    Path(tmp).replace(path)


class PlaylistStore:
    """playlist.json behind a lock: read once at startup, appended by requests."""

    def __init__(self, path: str):
        self.path = path
        self.lock = threading.Lock()

    def load(self) -> list[Track]:
        with self.lock:
            return load_playlist(self.path)

    def update_source(self, old_source: str, new_track: Track) -> bool:
        """Replace a track in the playlist file (e.g. after resolving ytsearch to a real URL)."""
        if not self.path or not old_source or not new_track:
            return False
        with self.lock:
            try:
                cur = load_playlist(self.path)
                changed = False
                for i, t in enumerate(cur):
                    if t.source == old_source:
                        cur[i] = new_track
                        changed = True
                        break
                if changed:
                    save_playlist(self.path, cur)
                    log.info("playlist: resolved %r -> %r in %s", old_source, new_track.source, self.path)
                    return True
                return False
            except Exception:
                log.exception("cannot update resolved track in playlist file %r", self.path)
                return False

    def add(self, tracks) -> int:
        """Append tracks to playlist.json (dedup by source). Returns how many were new.
        Disabled / nothing to add / write failure are all no-ops (never breaks the request)."""
        if not self.path or not tracks:
            return 0
        with self.lock:
            try:
                cur = load_playlist(self.path)
                if not cur and _unreadable(self.path):
                    bad = f"{self.path}.corrupt-{datetime.now():%Y%m%d-%H%M%S}"
                    shutil.copyfile(self.path, bad)  # keep the user's file; load_playlist promised not to overwrite it
                    log.warning("playlist file %r is unreadable: saved a copy as %r", self.path, bad)
                have = {t.source for t in cur}
                now = datetime.now().isoformat(timespec="seconds")
                fresh = []
                for t in tracks:
                    if t.source not in have:
                        have.add(t.source)
                        t.added = now
                        fresh.append(t)
                if not fresh:
                    return 0
                cur.extend(fresh)
                save_playlist(self.path, cur)
                log.info(
                    "playlist: +%d new source(s) -> %s (%d total)",
                    len(fresh),
                    self.path,
                    len(cur),
                )
                return len(fresh)
            except Exception:
                log.exception(
                    "cannot update playlist file %r (the request still went through)",
                    self.path,
                )
                return 0
