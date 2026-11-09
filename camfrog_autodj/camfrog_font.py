"""Camfrog desktop client font settings via Windows registry.

Camfrog stores IM/chat font settings in the Windows registry under keys such as
``IMFont``, ``IMFontSize``, ``FontName``, and ``FontName_VCHR``.  These are
**receiver-side display preferences** — they control how incoming text appears
in each user's own Camfrog client.  They do **not** affect outgoing messages
sent by AutoDJ, which are always plain text via UI Automation.

This module provides safe, never-crashing read/write access to those registry
keys so an operator can inspect or mirror Camfrog's font configuration from
AutoDJ.  All operations are Windows-only; on non-Windows platforms the module
gracefully degrades to no-ops.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import MessageStyle

log = __import__("logging").getLogger("autodj.camfrog_font")

_winreg_cache: object | None = None
winreg: object | None = None  # type: ignore[assignment]


def _get_winreg():
    """Return the winreg module on Windows, None otherwise.

    Tests can monkeypatch ``cf.winreg`` directly (set to a fake module) or
    set ``cf.os.name = "nt"`` to trigger a real import attempt.  Never raises.
    """
    global _winreg_cache
    # If a test has monkeypatched cf.winreg, honor it first.
    if winreg is not None:
        return winreg
    # On non-Windows, no registry access.
    if os.name != "nt":
        return None
    # Cache successful imports.
    if _winreg_cache is not None:
        return _winreg_cache
    try:
        import winreg as _wr  # type: ignore[import]

        _winreg_cache = _wr
        globals()["winreg"] = _wr
        return _wr
    except ImportError:  # pragma: no cover - winreg is stdlib on Windows
        return None


# Registry paths where Camfrog stores font settings (observed via REA of camfrog.exe).
_CAMFROG_REG_PATHS = (
    r"Software\Camfrog\Camfrog",
    r"Software\Camfrog Video Chat\Camfrog",
    r"Software\Camfrog\Settings\General",
    r"Software\Camfrog Video Chat\Settings\General",
    r"Software\Camfrog\ProfileInfo",
    r"Software\Camfrog Video Chat\ProfileInfo",
)

# Registry value names -> MessageStyle field names (best-effort mapping).
_REG_TO_STYLE: dict[str, str] = {
    "IMFont": "font_family",
    "IMFontSize": "font_size",
    "FontName": "font_family",
    "FontName_VCHR": "font_family",
}

# Reverse mapping for writing (only family and size are writable safely).
_STYLE_TO_REG: dict[str, str] = {
    "font_family": "IMFont",
    "font_size": "IMFontSize",
}


@dataclass
class CamfrogFontSettings:
    """Font settings read from Camfrog's Windows registry.

    All fields are optional — a missing or unreadable registry key simply leaves
    the field at its default.  This object is never the source of truth for
    AutoDJ's outgoing messages (plain text only); it is purely informational
    and for operators who want to mirror Camfrog's own font configuration.
    """

    im_font: str | None = None
    im_font_size: int | None = None
    font_name: str | None = None
    font_name_vchr: str | None = None
    source_path: str | None = None  # registry path that was actually read

    def to_message_style(self) -> "MessageStyle":
        """Convert to a :class:`MessageStyle` for GUI preview use.

        Only fields that were actually observed in the registry are applied;
        missing fields keep the :class:`MessageStyle` defaults.
        """
        from .config import MessageStyle

        style = MessageStyle()
        if self.im_font:
            style.font_family = self.im_font
        elif self.font_name:
            style.font_family = self.font_name
        if self.im_font_size is not None:
            style.font_size = self.im_font_size
        return style

    @classmethod
    def from_message_style(cls, style: "MessageStyle") -> "CamfrogFontSettings":
        """Build a :class:`CamfrogFontSettings` from a :class:`MessageStyle`
        for writing back to the registry."""
        return cls(
            im_font=style.font_family or None,
            im_font_size=style.font_size or None,
            font_name=style.font_family or None,
        )


# ---------------------------------------------------------------------------
# Windows registry access (never raises)
# ---------------------------------------------------------------------------


def _open_camfrog_key(writable: bool = False):
    """Try to open a Camfrog registry key.

    Returns ``(handle, path)`` on success, ``(None, None)`` if no Camfrog key
    exists or we are not on Windows.  Never raises.
    """
    wr = _get_winreg()
    if wr is None:
        return None, None

    access = wr.KEY_READ
    if writable:
        access |= wr.KEY_WRITE

    for path in _CAMFROG_REG_PATHS:
        try:
            key = wr.OpenKey(  # type: ignore[attr-defined]
                wr.HKEY_CURRENT_USER, path, 0, access
            )
            return key, path
        except (FileNotFoundError, OSError):
            continue
        except Exception:  # noqa: BLE001, S112 - never crash on registry access
            continue
    return None, None


def _query_value(key, valname: str):
    """Query a single registry value.  Returns the value or None."""
    wr = _get_winreg()
    if wr is None:
        return None
    try:
        val, _ = key.QueryValueEx(valname)  # type: ignore[attr-defined]
        return val
    except (FileNotFoundError, OSError):
        return None
    except Exception:  # noqa: BLE001 - never crash
        return None


def _set_value(key, valname: str, value) -> bool:
    """Set a single registry value.  Returns True on success."""
    wr = _get_winreg()
    if wr is None:
        return False
    try:
        if isinstance(value, int):
            key.SetValueEx(valname, 0, wr.REG_DWORD, value)  # type: ignore[attr-defined]
        else:
            key.SetValueEx(valname, 0, wr.REG_SZ, str(value))  # type: ignore[attr-defined]
        return True
    except (OSError, PermissionError):
        return False
    except Exception:  # noqa: BLE001 - never crash
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def read_camfrog_font_settings() -> CamfrogFontSettings:
    """Read Camfrog font settings from the Windows registry.

    Returns a :class:`CamfrogFontSettings` with whatever fields could be
    discovered.  Never raises — on non-Windows or when no Camfrog registry key
    exists, returns an empty settings object.
    """
    key, path = _open_camfrog_key(writable=False)
    if key is None:
        return CamfrogFontSettings()

    try:
        settings = CamfrogFontSettings(source_path=path)

        im_font = _query_value(key, "IMFont")
        if im_font:
            settings.im_font = str(im_font)

        im_font_size = _query_value(key, "IMFontSize")
        if im_font_size is not None:
            try:
                settings.im_font_size = int(im_font_size)
            except (ValueError, TypeError):
                pass

        font_name = _query_value(key, "FontName")
        if font_name:
            settings.font_name = str(font_name)

        font_name_vchr = _query_value(key, "FontName_VCHR")
        if font_name_vchr:
            settings.font_name_vchr = str(font_name_vchr)

        return settings
    finally:
        try:
            key.Close()
        except Exception:  # noqa: BLE001, S110
            pass


def write_camfrog_font_settings(settings: CamfrogFontSettings) -> bool:
    """Write Camfrog font settings to the Windows registry.

    Writes ``IMFont`` and ``IMFontSize`` to the first writable Camfrog registry
    key found.  Returns True if at least one value was written successfully.
    Never raises — on non-Windows or when no writable key exists, returns False.
    """
    key, _path = _open_camfrog_key(writable=True)
    if key is None:
        return False

    try:
        written = False
        if settings.im_font:
            if _set_value(key, "IMFont", settings.im_font):
                written = True
        if settings.im_font_size is not None:
            if _set_value(key, "IMFontSize", settings.im_font_size):
                written = True
        return written
    finally:
        try:
            key.Close()
        except Exception:  # noqa: BLE001, S110
            pass


def sync_message_style_to_camfrog(style: "MessageStyle") -> bool:
    """Convenience: write a :class:`MessageStyle` to Camfrog's registry.

    Returns True if any value was written.  Never raises.
    """
    fs = CamfrogFontSettings.from_message_style(style)
    return write_camfrog_font_settings(fs)


def is_windows() -> bool:
    """Return True if running on Windows (registry access available)."""
    return os.name == "nt"
