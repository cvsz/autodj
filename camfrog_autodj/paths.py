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
        expanded = expanded.replace("\\\\", os.sep)

    def replace(match: re.Match[str]) -> str:
        return os.environ.get(match.group(1), match.group(0))

    return re.sub(r"%([^%]+)%", replace, expanded)


def resolve_executable(configured: str | None, fallback: str = "") -> str:
    """Resolve an executable path or PATH command to an absolute file path.

    Explicit paths are authoritative: if they do not exist, return an empty string
    instead of silently selecting a different executable. Relative paths containing
    a separator are anchored to the application directory.
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
            return str(candidate.resolve())
    except OSError:
        return ""

    if not has_separator:
        found = shutil.which(expanded)
        if found:
            return str(Path(found).resolve())

    return ""
