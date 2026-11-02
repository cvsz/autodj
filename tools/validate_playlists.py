"""Validate and optionally fix playlist/*.json source URLs.

Checks every track source in playlist/*.json:
- http(s):// URLs: valid
- ytsearchN: queries: valid for yt-dlp (search at play time)
- Everything else: flagged as invalid

Usage:
    python tools/validate_playlists.py          # report only
    python tools/validate_playlists.py --fix    # report + remove invalid entries
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

URL_RE = re.compile(r"^https?://", re.IGNORECASE)
SEARCH_RE = re.compile(r"^ytsearch\d+:", re.IGNORECASE)


def is_valid_source(source: str) -> bool:
    """Return True if source is a valid URL or yt-dlp search query."""
    if not source or not isinstance(source, str):
        return False
    s = source.strip()
    if not s:
        return False
    return bool(URL_RE.match(s) or SEARCH_RE.match(s))


def validate_file(path: Path) -> tuple[int, int, list[tuple[int, str, str]]]:
    """Validate a single playlist file.

    Returns (total_tracks, invalid_count, invalid_entries)
    where invalid_entries is (index, source, reason).
    """
    try:
        data = json.loads(path.read_text("utf-8-sig"))
    except Exception as exc:
        return 0, 1, [(0, str(path), f"invalid JSON: {exc}")]

    tracks = data.get("tracks", []) if isinstance(data, dict) else data
    if not isinstance(tracks, list):
        return 0, 1, [(0, str(path), "tracks is not a list")]

    invalid: list[tuple[int, str, str]] = []
    for i, t in enumerate(tracks):
        source = t.get("source", "") if isinstance(t, dict) else str(t)
        if not is_valid_source(source):
            reason = "empty" if not str(source).strip() else "not a URL or ytsearch query"
            invalid.append((i, str(source), reason))

    return len(tracks), len(invalid), invalid


def fix_file(path: Path, dry_run: bool = False) -> int:
    """Remove invalid entries from a playlist file. Returns number removed."""
    try:
        data = json.loads(path.read_text("utf-8-sig"))
    except Exception:
        return 0

    tracks = data.get("tracks", []) if isinstance(data, dict) else data
    if not isinstance(tracks, list):
        return 0

    valid = [t for t in tracks if is_valid_source(t.get("source", "")) if isinstance(t, dict)]
    removed = len(tracks) - len(valid)

    if removed > 0 and not dry_run:
        backup = path.with_suffix(f".json.invalid-{datetime.now():%Y%m%d-%H%M%S}.bak")
        shutil.copyfile(path, backup)
        if isinstance(data, dict):
            data["tracks"] = valid
        else:
            data = valid
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=1), "utf-8"
        )
        print(f"  fixed {path.name}: removed {removed} invalid entr{'y' if removed == 1 else 'ies'} (backup: {backup.name})")

    return removed


def main() -> None:
    ap = argparse.ArgumentParser(description="Validate playlist/*.json source URLs")
    ap.add_argument("--fix", action="store_true", help="remove invalid entries (with .bak backup)")
    ap.add_argument("--dir", default="playlist", help="playlist directory (default: playlist)")
    args = ap.parse_args()

    pl_dir = Path(args.dir)
    if not pl_dir.is_dir():
        print(f"Directory not found: {pl_dir}")
        return

    files = sorted(pl_dir.glob("*.json"))
    if not files:
        print(f"No *.json files found in {pl_dir}")
        return

    total_tracks = 0
    total_invalid = 0
    total_removed = 0

    for f in files:
        n_tracks, n_invalid, invalid = validate_file(f)
        total_tracks += n_tracks
        total_invalid += n_invalid

        status = "OK" if n_invalid == 0 else f"{n_invalid} INVALID"
        print(f"{f.name}: {n_tracks} tracks, {status}")

        for idx, src, reason in invalid:
            print(f"  [{idx}] {reason}: {src[:80]}")

        if args.fix and n_invalid > 0:
            total_removed += fix_file(f, dry_run=False)

    print()
    print(f"Total: {total_tracks} tracks across {len(files)} file(s)")
    print(f"Invalid: {total_invalid}")
    if args.fix:
        print(f"Removed: {total_removed}")


if __name__ == "__main__":
    main()
