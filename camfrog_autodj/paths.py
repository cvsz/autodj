"""Executable path resolution shared by playback and diagnostics."""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path


def application_dir() -> Path:
    """Return the directory containing the frozen app, or the current project directory."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd().resolve()


def _expand_environment(value: str) -> str:
    """Expand POSIX and Windows environment-variable syntax on every host."""
    expanded = os.path.expanduser(os.path.expandvars(value))
    if os.name != "nt":
        expanded = expanded.replace("\\", os.sep)

    def replace(match: re.Match[str]) -> str:
        return os.environ.get(match.group(1), match.group(0))

    return re.sub(r"%([^%]+)%", replace, expanded)


def log_directory() -> Path:
    """Return the install-folder ``logs`` directory (APPDATA fallback).

    AutoDJ stores ``*.log`` next to the running installation so operators can
    inspect actions from the same folder.  If the install folder is read-only
    (e.g. Program Files), fall back to a user-writable APPDATA location.
    """
    install_logs = application_dir() / "logs"
    try:
        install_logs.mkdir(parents=True, exist_ok=True)
        probe = install_logs / ".write_probe"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return install_logs
    except OSError:
        app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
        fallback = Path(app_data) / "CamfrogAutoDJ" / "logs"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def resolve_log_path(configured: str | None = None) -> Path:
    """Resolve a configured log filename to a path under the logs directory."""
    raw = (configured or "").strip()
    if not raw:
        return log_directory() / "autodj.log"
    expanded = _expand_environment(raw)
    candidate = Path(expanded)
    if candidate.is_absolute():
        return candidate
    # Existing configs commonly use "logs/autodj.log"; avoid logs/logs nesting.
    relative = expanded.replace("\\", "/")
    if relative.lower().startswith("logs/"):
        relative = relative[5:]
    return log_directory() / relative


def resolve_executable(
    configured: str | None, fallback: str = "", *, only_exe: bool = False
) -> str:
    """Resolve an executable path or PATH command to an absolute file path.

    Explicit paths are authoritative: if they do not exist, return an empty string
    instead of silently selecting a different executable. Relative paths containing
    a separator are anchored to the application directory.

    ``only_exe`` (used for mpv) never returns a ``.com`` shim: it prefers the
    sibling ``.exe`` and asks PATH specifically for ``<name>.exe``, because on
    Windows PATHEXT usually puts ``.COM`` before ``.EXE``.
    """
    raw = (configured or fallback or "").strip()
    if not raw:
        return ""

    expanded = _expand_environment(raw)
    has_separator = "/" in expanded or "\\" in expanded
    candidate = Path(expanded)

    if not candidate.is_absolute() and has_separator:
        candidate = application_dir() / candidate

    try:
        if candidate.is_file():
            if only_exe and candidate.suffix.lower() == ".com":
                sibling = candidate.with_suffix(".exe")
                return str(sibling.resolve()) if sibling.is_file() else ""
            return str(candidate.resolve())
    except OSError:
        return ""

    if not has_separator:
        if only_exe and os.name == "nt":
            name = expanded if expanded.lower().endswith(".exe") else expanded + ".exe"
            return shutil.which(name) or ""
        found = shutil.which(expanded)
        if found:
            if only_exe and found.lower().endswith(".com"):
                sibling = Path(found).with_suffix(".exe")
                return str(sibling.resolve()) if sibling.is_file() else ""
            return found

    return ""
