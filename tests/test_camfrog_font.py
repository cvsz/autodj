"""Tests for camfrog_font.py — Camfrog desktop client font registry access."""

from __future__ import annotations

from unittest.mock import MagicMock

import camfrog_autodj.camfrog_font as cf
from camfrog_autodj.config import MessageStyle

# ---------------------------------------------------------------------------
# is_windows
# ---------------------------------------------------------------------------


def test_is_windows_on_windows(monkeypatch):
    monkeypatch.setattr(cf.os, "name", "nt")
    assert cf.is_windows() is True


def test_is_windows_on_linux(monkeypatch):
    monkeypatch.setattr(cf.os, "name", "posix")
    assert cf.is_windows() is False


# ---------------------------------------------------------------------------
# read_camfrog_font_settings — non-Windows
# ---------------------------------------------------------------------------


def test_read_camfrog_font_settings_non_windows(monkeypatch):
    """On non-Windows, returns empty settings without error."""
    monkeypatch.setattr(cf.os, "name", "posix")
    settings = cf.read_camfrog_font_settings()
    assert settings.im_font is None
    assert settings.im_font_size is None
    assert settings.font_name is None
    assert settings.font_name_vchr is None
    assert settings.source_path is None


# ---------------------------------------------------------------------------
# Helper: mocked winreg key
# ---------------------------------------------------------------------------


def _make_mock_key(values: dict):
    """Build a mock winreg key object that supports QueryValueEx and Close."""
    key = MagicMock()

    def query_value_ex(valname):
        if valname in values:
            return values[valname], None
        raise FileNotFoundError(valname)

    key.__enter__.return_value = key
    key.__exit__.return_value = False
    key.QueryValueEx.side_effect = query_value_ex
    return key


def _patch_winreg(monkeypatch, open_key_side_effect=None):
    """Patch winreg module and return the fake module + mock key."""
    # Reset cache so each test starts fresh
    cf._winreg_cache = None
    cf.winreg = None

    fake_winreg = MagicMock()
    fake_winreg.HKEY_CURRENT_USER = "HKCU"
    fake_winreg.KEY_READ = 0
    fake_winreg.KEY_WRITE = 0
    fake_winreg.REG_DWORD = 4
    fake_winreg.REG_SZ = 1

    mock_key = MagicMock()
    mock_key.__enter__.return_value = mock_key
    mock_key.__exit__.return_value = False

    if open_key_side_effect is not None:
        fake_winreg.OpenKey.side_effect = open_key_side_effect
    else:
        fake_winreg.OpenKey.return_value = mock_key

    # Patch the module attribute that _open_camfrog_key uses
    monkeypatch.setattr(cf, "winreg", fake_winreg)
    return fake_winreg, mock_key


# ---------------------------------------------------------------------------
# read_camfrog_font_settings — Windows
# ---------------------------------------------------------------------------


def test_read_camfrog_font_settings_reads_all_fields(monkeypatch):
    monkeypatch.setattr(cf.os, "name", "nt")

    fake_winreg, mock_key = _patch_winreg(monkeypatch)

    values = {
        "IMFont": ("Segoe UI", None),
        "IMFontSize": (12, None),
        "FontName": ("Arial", None),
        "FontName_VCHR": ("Tahoma", None),
    }

    def query_side_effect(valname):
        if valname in values:
            return values[valname]
        raise FileNotFoundError(valname)

    mock_key.QueryValueEx.side_effect = query_side_effect

    settings = cf.read_camfrog_font_settings()
    assert settings.im_font == "Segoe UI"
    assert settings.im_font_size == 12
    assert settings.font_name == "Arial"
    assert settings.font_name_vchr == "Tahoma"
    assert settings.source_path is not None


def test_read_camfrog_font_settings_missing_key(monkeypatch):
    """When no Camfrog registry key exists, returns empty settings."""
    monkeypatch.setattr(cf.os, "name", "nt")

    fake_winreg, mock_key = _patch_winreg(
        monkeypatch, open_key_side_effect=FileNotFoundError("no such key")
    )

    settings = cf.read_camfrog_font_settings()
    assert settings.im_font is None
    assert settings.im_font_size is None
    assert settings.font_name is None
    assert settings.font_name_vchr is None
    assert settings.source_path is None


def test_read_camfrog_font_settings_partial_fields(monkeypatch):
    """When only some fields exist, returns those fields only."""
    monkeypatch.setattr(cf.os, "name", "nt")

    fake_winreg, mock_key = _patch_winreg(monkeypatch)

    def query_side_effect(valname):
        if valname == "IMFont":
            return ("Consolas", None)
        raise FileNotFoundError(valname)

    mock_key.QueryValueEx.side_effect = query_side_effect

    settings = cf.read_camfrog_font_settings()
    assert settings.im_font == "Consolas"
    assert settings.im_font_size is None
    assert settings.font_name is None


# ---------------------------------------------------------------------------
# write_camfrog_font_settings — non-Windows
# ---------------------------------------------------------------------------


def test_write_camfrog_font_settings_non_windows(monkeypatch):
    monkeypatch.setattr(cf.os, "name", "posix")
    settings = cf.CamfrogFontSettings(im_font="Consolas", im_font_size=14)
    assert cf.write_camfrog_font_settings(settings) is False


# ---------------------------------------------------------------------------
# write_camfrog_font_settings — Windows
# ---------------------------------------------------------------------------


def test_write_camfrog_font_settings_writes(monkeypatch):
    monkeypatch.setattr(cf.os, "name", "nt")

    fake_winreg, mock_key = _patch_winreg(monkeypatch)

    settings = cf.CamfrogFontSettings(im_font="Consolas", im_font_size=14)
    assert cf.write_camfrog_font_settings(settings) is True

    # Verify SetValueEx was called for both values
    names = [c.args[0] for c in mock_key.SetValueEx.call_args_list]
    assert "IMFont" in names
    assert "IMFontSize" in names


def test_write_camfrog_font_settings_only_family(monkeypatch):
    monkeypatch.setattr(cf.os, "name", "nt")

    fake_winreg, mock_key = _patch_winreg(monkeypatch)

    settings = cf.CamfrogFontSettings(im_font="Consolas")
    assert cf.write_camfrog_font_settings(settings) is True

    names = [c.args[0] for c in mock_key.SetValueEx.call_args_list]
    assert "IMFont" in names
    assert "IMFontSize" not in names


# ---------------------------------------------------------------------------
# sync_message_style_to_camfrog
# ---------------------------------------------------------------------------


def test_sync_message_style_to_camfrog_non_windows(monkeypatch):
    monkeypatch.setattr(cf.os, "name", "posix")
    style = MessageStyle(font_family="Consolas", font_size=14)
    assert cf.sync_message_style_to_camfrog(style) is False


# ---------------------------------------------------------------------------
# CamfrogFontSettings.to_message_style / from_message_style
# ---------------------------------------------------------------------------


def test_to_message_style_applies_observed_fields():
    settings = cf.CamfrogFontSettings(
        im_font="Consolas", im_font_size=14, source_path=r"Software\Camfrog\Camfrog"
    )
    style = settings.to_message_style()
    assert style.font_family == "Consolas"
    assert style.font_size == 14


def test_to_message_style_keeps_defaults_when_empty():
    settings = cf.CamfrogFontSettings()
    style = settings.to_message_style()
    assert style.font_family == "Consolas"  # MessageStyle default
    assert style.font_size == 14  # MessageStyle default


def test_from_message_style():
    style = MessageStyle(font_family="Arial", font_size=16)
    settings = cf.CamfrogFontSettings.from_message_style(style)
    assert settings.im_font == "Arial"
    assert settings.im_font_size == 16


def test_roundtrip():
    style = MessageStyle(font_family="Segoe UI", font_size=12, bold=True)
    settings = cf.CamfrogFontSettings.from_message_style(style)
    style2 = settings.to_message_style()
    assert style2.font_family == "Segoe UI"
    assert style2.font_size == 12


# ---------------------------------------------------------------------------
# Import guard on non-Windows (module must import cleanly everywhere)
# ---------------------------------------------------------------------------


def test_module_imports_on_non_windows():
    """The module must import cleanly on any platform."""
    assert cf is not None
    assert callable(cf.read_camfrog_font_settings)
    assert callable(cf.write_camfrog_font_settings)
    assert callable(cf.sync_message_style_to_camfrog)
