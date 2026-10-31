"""Optionally start the official Camfrog client and hand off to a room, then wait for its window.
Windows only. This does not use the control-server API: if the control-server agent already
launches/joins for you, leave auto_launch=false and AutoDJ just waits for the window."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from urllib.parse import quote

log = logging.getLogger("autodj")


def _require_windows() -> None:
    if sys.platform != "win32":
        raise RuntimeError("Camfrog launcher is Windows-only")


def find_window(pattern: str, timeout: float) -> bool:
    from .windows import resolve

    return resolve(pattern, timeout=timeout) is not None


def _open_uri(uri: str):
    _require_windows()
    os.startfile(uri)  # type: ignore[attr-defined]  # Windows only


def _start(exe: str):
    _require_windows()
    subprocess.Popen([exe])


def ensure_room(cfg) -> None:
    if not find_window(cfg.client_title_re, 1):
        if not cfg.camfrog_exe:
            raise RuntimeError("Camfrog is not running and camfrog_exe is not set")
        log.info("starting %s", cfg.camfrog_exe)
        _start(cfg.camfrog_exe)
        if not find_window(cfg.client_title_re, cfg.launch_timeout):
            raise RuntimeError("Camfrog window did not appear")
    if cfg.room:
        if not cfg.join_uri_template:
            log.warning("room is set but join_uri_template is empty; skipping auto-join")
        else:
            uri = cfg.join_uri_template.format(room=quote(cfg.room))
            log.info("joining room via %s", uri)
            _open_uri(uri)
    if not find_window(cfg.window_title_re, cfg.launch_timeout):
        raise RuntimeError(f"room window not found: {cfg.window_title_re}")
