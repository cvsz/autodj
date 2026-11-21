"""Regression tests for the 2026-11-21 audit (mute wording, shipped log paths)."""

from __future__ import annotations

import os
from pathlib import Path

from autodj.config import Config
from autodj.messages import STR
from autodj.paths import resolve_log_path

ROOT = Path(__file__).resolve().parent.parent


def test_mute_messages_say_music_not_mic():
    """!mute only sets AutoDJ's player volume to 0; the room was told 'Mic muted.'."""
    for lang in ("en", "th"):
        for key in ("mute_on", "mute_off", "mute_state", "g_settings_mute_enabled"):
            text = STR[lang][key]
            assert "mic" not in text.lower() and "ไมโครโฟน" not in text, (lang, key, text)


def test_example_config_does_not_log_to_shared_appdata_logs():
    """config.example.toml sent logs to %APPDATA%\\logs, a folder shared by every app."""
    cfg = Config.load(str(ROOT / "config.example.toml"))
    assert cfg.log_file == ""
    assert cfg.log_path == ""
    resolved = resolve_log_path(cfg.log_file)
    assert resolved.name == "autodj.log"
    appdata = os.environ.get("APPDATA")
    if appdata:
        assert resolved.parent != Path(appdata) / "logs"
