"""Configuration migration: detect placeholder/invalid values and discover valid paths.

Called at AutoDJ startup and on ``--check`` to repair configurations that contain
placeholder values (e.g. ``mpv_path = "REPLACE_ME"``) left by the installer or
earlier versions.  Never replaces valid custom operator values with defaults.
Always backs up config.toml before writing.
"""

from __future__ import annotations

import logging
import os
import tomllib
from pathlib import Path

from .discover import save_config
from .paths import _expand_environment, application_dir

log = logging.getLogger("autodj")

# Tokens that indicate a value was left as a placeholder by the installer or
# an earlier version and needs to be replaced with a real path.
PLACEHOLDER_TOKENS = (
    "replace_me",
    "replace-me",
    "change_me",
    "change-me",
    "your_path_here",
    "path_here",
    "todo",
    "fixme",
    "xxx",
)

# Relative locations (from the config file's directory) where bundled
# executables are typically installed by the NSIS installer.
RELATIVE_EXECUTABLE_PATHS: dict[str, tuple[str, ...]] = {
    "mpv_path": ("mpv/mpv.exe", "mpv/mpv.com"),
    "ytdlp_path": ("mpv/yt-dlp.exe", "yt-dlp.exe"),
}

# Common Windows locations for bundled tools (fallback when nothing is
# discoverable relative to the config file or in the registry).
COMMON_WINDOWS_PATHS: dict[str, tuple[str, ...]] = {
    "mpv_path": (
        "C:/mpv/mpv.exe",
        "C:/Program Files/mpv/mpv.exe",
    ),
    "ytdlp_path": ("C:/mpv/yt-dlp.exe",),
}


def _is_placeholder(value: str) -> bool:
    """Return True if *value* looks like an installer placeholder."""
    v = value.strip().strip('"').strip("'").lower()
    if not v:
        return True  # empty string for a path that should be set
    for token in PLACEHOLDER_TOKENS:
        if token in v:
            return True
    return False


def _discover_path(
    key: str, config_dir: Path, registry_value: str | None = None
) -> str | None:
    """Discover a valid executable path for a config key.

    Search order:
      1. Registry value (set by the NSIS installer on upgrade/install)
      2. Relative to the config file's directory (installation directory)
      3. Relative to the application directory (frozen exe)
      4. Common Windows locations
    """
    candidates: list[str] = []

    if registry_value:
        candidates.append(registry_value)

    for rel in RELATIVE_EXECUTABLE_PATHS.get(key, ()):
        candidates.append(str(config_dir / rel))

    app_dir = application_dir()
    for rel in RELATIVE_EXECUTABLE_PATHS.get(key, ()):
        candidates.append(str(app_dir / rel))

    candidates.extend(COMMON_WINDOWS_PATHS.get(key, ()))

    for candidate in candidates:
        expanded = _expand_environment(candidate)
        p = Path(expanded)
        if not p.is_absolute():
            p = application_dir() / p
        try:
            if p.is_file():
                return str(p.resolve())
        except OSError:
            continue
    return None


def _read_registry_values() -> dict[str, str]:
    """Read mpv_path and ytdlp_path from the Windows registry (set by installer).

    Returns an empty dict on non-Windows or when the registry key is absent.
    Never raises.
    """
    if os.name != "nt":
        return {}
    try:
        import winreg

        values: dict[str, str] = {}
        try:
            with winreg.OpenKey(  # type: ignore[attr-defined]
                winreg.HKEY_CURRENT_USER,  # type: ignore[attr-defined]
                r"Software\CamfrogAutoDJ",
            ) as key:
                for valname in ("mpv_path", "ytdlp_path"):
                    try:
                        values[valname] = (  # type: ignore[attr-defined]
                            winreg.QueryValueEx(key, valname)[0]  # type: ignore[attr-defined]
                        )
                    except FileNotFoundError:
                        pass
        except FileNotFoundError:
            pass
        return values
    except Exception:  # noqa: BLE001 - never let registry reads crash startup
        return {}


def detect_placeholders(text: str) -> dict[str, str]:
    """Scan config text for placeholder/invalid values.

    Returns {key: raw_value} for keys whose values look like placeholders.
    Only checks keys that are known executable paths (mpv_path, ytdlp_path).
    """
    found: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        if key not in ("mpv_path", "ytdlp_path"):
            continue
        # Strip inline comment
        val_part = value.split("#", 1)[0].strip()
        # Strip surrounding quotes
        if (val_part.startswith('"') and val_part.endswith('"')) or (
            val_part.startswith("'") and val_part.endswith("'")
        ):
            val_part = val_part[1:-1]
        if _is_placeholder(val_part):
            found[key] = val_part
    return found


def migrate_config(config_path: str | Path) -> list[str]:
    """Migrate config.toml: detect placeholders, discover valid paths,
    back up and write.

    Returns a list of human-readable change descriptions.  An empty list means
    no changes were needed or no migratable placeholders were found.

    Never replaces valid custom operator values with defaults.  If no valid
    path can be discovered for a placeholder, the placeholder is left as-is
    and a warning is logged.
    """
    p = Path(config_path)
    if not p.exists():
        return []

    try:
        text = p.read_text("utf-8-sig")
    except (OSError, UnicodeDecodeError) as ex:
        log.warning("cannot read config %r for migration: %s", p, ex)
        return []

    try:
        tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        log.warning("config %r is not valid TOML; skipping migration", p)
        return []

    placeholders = detect_placeholders(text)
    if not placeholders:
        return []

    registry_values = _read_registry_values()
    config_dir = p.parent

    updates: dict[str, str] = {}
    changes: list[str] = []

    for key, placeholder_value in placeholders.items():
        discovered = _discover_path(key, config_dir, registry_values.get(key))
        if discovered:
            updates[key] = discovered
            changes.append(
                f"{key}: replaced placeholder '{placeholder_value}' with '{discovered}'"
            )
        else:
            changes.append(
                f"{key}: placeholder '{placeholder_value}' kept (no valid path discovered)"
            )

    if not updates:
        # Report placeholders that couldn't be resolved, but don't modify the file
        return changes

    # save_config() handles backup (.bak), atomic write (.tmp + replace),
    # comment preservation, and TOML re-validation.
    if save_config(str(p), updates):
        log.info("config migrated: %d change(s) in %s", len(updates), p)
        return changes

    log.warning("config migration write failed for %r", p)
    return changes


def migration_needed(config_path: str | Path) -> bool:
    """Return True if config.toml contains migratable placeholder values."""
    p = Path(config_path)
    if not p.exists():
        return False
    try:
        text = p.read_text("utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return False
    return bool(detect_placeholders(text))
