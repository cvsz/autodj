"""Tests for configuration migration (Workstream C).

Tests:
- Fresh installation: no config file, no migration needed
- Upgrade from 0.2.4: config with mpv_path = "REPLACE_ME" is migrated
- Existing custom configuration: valid values are preserved
- Missing executables: placeholder kept when no valid path found
- Invalid placeholder values: detected and reported
- Configuration backup and preservation: .bak file created
"""

from __future__ import annotations

import os
import pathlib
from pathlib import Path

import pytest

from camfrog_autodj.migrate import detect_placeholders, migrate_config, migration_needed


def _write_config(tmp_path, text):
    p = tmp_path / "config.toml"
    p.write_text(text, "utf-8")
    return str(p)


# ---- Fresh installation ----

def test_no_config_file_no_migration(tmp_path):
    """No config file: migration returns empty list."""
    p = tmp_path / "nonexistent.toml"
    assert migrate_config(str(p)) == []


def test_config_without_placeholders_no_migration(tmp_path):
    """Valid config with no placeholders: no changes."""
    p = _write_config(
        tmp_path,
        'mpv_path = "C:/mpv/mpv.exe"\nytdlp_path = "C:/mpv/yt-dlp.exe"\n',
    )
    assert migrate_config(str(p)) == []
    assert migration_needed(str(p)) is False


# ---- Upgrade from 0.2.4: placeholder values ----

def test_migrate_mpv_path_placeholder(tmp_path, monkeypatch):
    """mpv_path = "REPLACE_ME" is replaced with discovered path."""
    # Create mpv.exe next to config dir (simulating NSIS install layout)
    config_dir = tmp_path
    mpv_dir = config_dir / "mpv"
    mpv_dir.mkdir()
    (mpv_dir / "mpv.exe").write_text("fake mpv")

    p = _write_config(
        tmp_path,
        'bot_nick = "AutoDJ"\nmpv_path = "REPLACE_ME"\nytdlp_path = ""\n',
    )
    changes = migrate_config(str(p))
    assert any("mpv_path" in c and "replaced" in c for c in changes), changes

    # Verify the config was updated
    from camfrog_autodj.config import Config
    cfg = Config.load(str(p))
    assert "mpv.exe" in cfg.mpv_path


def test_migrate_ytdlp_path_placeholder(tmp_path, monkeypatch):
    """ytdlp_path = "REPLACE_ME" is replaced with discovered path."""
    config_dir = tmp_path
    mpv_dir = config_dir / "mpv"
    mpv_dir.mkdir()
    (mpv_dir / "yt-dlp.exe").write_text("fake yt-dlp")

    p = _write_config(
        tmp_path,
        'bot_nick = "AutoDJ"\nmpv_path = "C:/mpv/mpv.exe"\nytdlp_path = "REPLACE_ME"\n',
    )
    changes = migrate_config(str(p))
    assert any("ytdlp_path" in c and "replaced" in c for c in changes), changes

    from camfrog_autodj.config import Config
    cfg = Config.load(str(p))
    assert "yt-dlp.exe" in cfg.ytdlp_path


# ---- Existing custom configuration preserved ----

def test_custom_values_preserved(tmp_path, monkeypatch):
    """Valid custom mpv_path is not replaced even if a placeholder exists elsewhere."""
    config_dir = tmp_path
    mpv_dir = config_dir / "mpv"
    mpv_dir.mkdir()
    (mpv_dir / "mpv.exe").write_text("fake mpv")
    (mpv_dir / "yt-dlp.exe").write_text("fake yt-dlp")

    p = _write_config(
        tmp_path,
        'bot_nick = "MyCustomBot"\n'
        'mpv_path = "C:/Custom/Path/mpv.exe"\n'
        'ytdlp_path = "REPLACE_ME"\n'
        'volume = 85\n'
        'lang = "th"\n',
    )
    changes = migrate_config(str(p))
    # ytdlp_path should be migrated, mpv_path should be preserved
    assert any("ytdlp_path" in c and "replaced" in c for c in changes), changes
    assert not any("mpv_path" in c and "replaced" in c for c in changes), changes

    from camfrog_autodj.config import Config
    cfg = Config.load(str(p))
    assert cfg.mpv_path == "C:/Custom/Path/mpv.exe"  # preserved
    assert cfg.bot_nick == "MyCustomBot"  # preserved
    assert cfg.volume == 85  # preserved
    assert cfg.lang == "th"  # preserved


# ---- Missing executables ----

def test_placeholder_kept_when_no_valid_path(tmp_path, monkeypatch):
    """When no valid executable can be discovered, placeholder is kept."""
    # No mpv.exe anywhere: mock application_dir to return empty dir
    import camfrog_autodj.migrate as migrate_mod

    monkeypatch.setattr(
        migrate_mod, "application_dir", lambda: Path(tmp_path / "no-exe-here")
    )

    p = _write_config(
        tmp_path,
        'mpv_path = "REPLACE_ME"\n',
    )
    changes = migrate_config(str(p))
    assert any("kept" in c for c in changes), changes

    # Config should be unchanged
    from camfrog_autodj.config import Config
    cfg = Config.load(str(p))
    assert cfg.mpv_path == "REPLACE_ME"


# ---- Configuration backup ----

def test_migration_creates_backup(tmp_path, monkeypatch):
    """Migration creates a .bak backup before writing."""
    config_dir = tmp_path
    mpv_dir = config_dir / "mpv"
    mpv_dir.mkdir()
    (mpv_dir / "mpv.exe").write_text("fake mpv")

    original = 'mpv_path = "REPLACE_ME"\n'
    p = Path(_write_config(tmp_path, original))
    migrate_config(str(p))

    bak = p.with_suffix(p.suffix + ".bak")
    assert bak.exists(), "Backup file should be created"
    assert bak.read_text("utf-8") == original, "Backup should contain original content"

    # Original should have been modified
    assert p.read_text("utf-8") != original


# ---- Placeholder detection ----

def test_detect_placeholders_various_forms():
    """Various placeholder forms are detected."""
    text = '''
    mpv_path = "REPLACE_ME"
    ytdlp_path = "replace_me"
    bot_nick = "AutoDJ"
    '''
    found = detect_placeholders(text)
    assert "mpv_path" in found
    assert "ytdlp_path" in found
    assert "bot_nick" not in found


def test_detect_empty_string_is_placeholder():
    """Empty string for mpv_path is treated as placeholder."""
    text = 'mpv_path = ""\n'
    found = detect_placeholders(text)
    assert "mpv_path" in found


def test_detect_no_placeholder_for_valid_path():
    """Valid path is not detected as placeholder."""
    text = 'mpv_path = "C:/mpv/mpv.exe"\n'
    found = detect_placeholders(text)
    assert found == {}


def test_migration_needed_true_false(tmp_path):
    """migration_needed returns correct boolean."""
    p1 = _write_config(tmp_path, 'mpv_path = "REPLACE_ME"\n')
    assert migration_needed(str(p1)) is True

    p2 = _write_config(tmp_path, 'mpv_path = "C:/mpv/mpv.exe"\n')
    assert migration_needed(str(p2)) is False


# ---- Non-Windows: registry not used ----

def test_migrate_no_registry_on_non_windows(tmp_path, monkeypatch):
    """On non-Windows, registry is not consulted (no crash)."""
    monkeypatch.setattr(os, "name", "posix")
    config_dir = tmp_path
    mpv_dir = config_dir / "mpv"
    mpv_dir.mkdir()
    (mpv_dir / "mpv.exe").write_text("fake mpv")

    p = _write_config(tmp_path, 'mpv_path = "REPLACE_ME"\n')
    changes = migrate_config(str(p))
    # Should still discover via relative path
    assert any("replaced" in c for c in changes), changes
