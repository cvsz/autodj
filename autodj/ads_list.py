"""ads-list.json: the messages the auto-reply (auto ads) loop posts to the room.

Read by ``Engine._auto_reply_loop`` and edited from the GUI (Settings -> Ads list).
Accepted file formats (read): ``{"version": 1, "messages": [...]}``, a bare list,
or a dict with an ``ads`` / ``entries`` / ``items`` list. Always written as
``{"version": 1, "messages": [...]}``.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

log = logging.getLogger("autodj")

# Camfrog trims very long room lines; a longer ad is a typo, not an ad.
MAX_AD_CHARS = 1000
MAX_ADS = 500
_LIST_KEYS = ("messages", "ads", "entries", "items")


def resolve_path(auto_reply_file: str, cfg_path: str | None) -> str:
    """``auto_reply_file`` relative to the config file's folder (as the engine reads it)."""
    if not os.path.isabs(auto_reply_file) and cfg_path:
        return str(Path(cfg_path).parent / auto_reply_file)
    return auto_reply_file


def _entries(data: object, path: str) -> list:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in _LIST_KEYS:
            if isinstance(data.get(key), list):
                return list(data[key])
        log.warning(
            "auto-reply file %r: no valid messages list found (tried keys: %s)",
            path,
            ", ".join(_LIST_KEYS),
        )
        return []
    log.warning("auto-reply file %r: root must be a list or dict", path)
    return []


def clean(messages: object) -> list[str]:
    """Non-empty, stripped strings; ``None`` entries are dropped."""
    out: list[str] = []
    for m in messages if isinstance(messages, list) else []:
        if m is None:
            continue
        s = str(m).strip()
        if s:
            out.append(s)
    return out


def load(path: str) -> list[str]:
    """The ads in *path*; ``[]`` when the file is missing or not valid JSON."""
    try:
        data = json.loads(Path(path).read_text("utf-8-sig"))
    except FileNotFoundError:
        log.debug("auto-reply file %r not found", path)
        return []
    except json.JSONDecodeError as ex:
        log.warning("auto-reply file %r has invalid JSON: %s", path, ex)
        return []
    except OSError:
        log.warning("cannot read auto-reply file %r", path, exc_info=True)
        return []
    messages = clean(_entries(data, path))
    if not messages:
        log.warning("auto-reply file %r: no valid messages after filtering", path)
    return messages


def validate(messages: list[str]) -> list[str]:
    """Cleaned *messages*; raises ValueError for one that is too long or too many."""
    out = clean(messages)
    if len(out) > MAX_ADS:
        raise ValueError(f"too many ads ({len(out)} > {MAX_ADS})")
    for i, m in enumerate(out, 1):
        if len(m) > MAX_AD_CHARS:
            raise ValueError(f"ad {i} is {len(m)} characters (max {MAX_AD_CHARS})")
    return out


def save(path: str, messages: list[str]) -> list[str]:
    """Write *messages* atomically (temp file -> os.replace), keeping ``<file>.bak``.

    Returns the cleaned list that was written. Raises ValueError (see validate) or
    OSError; the existing file is untouched on any failure.
    """
    out = validate(messages)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps({"version": 1, "messages": out}, ensure_ascii=False, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=".ads-", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        if target.exists():
            bak = target.with_name(target.name + ".bak")
            bak.write_bytes(target.read_bytes())
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    log.info("ads list saved: %d message(s) -> %s", len(out), path)
    return out


def mtime(path: str) -> float | None:
    """Modification time of *path*, or None when it does not exist."""
    try:
        return os.stat(path).st_mtime
    except OSError:
        return None
