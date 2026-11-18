"""Tests for the zPlayer theme system and its configuration wiring."""

from __future__ import annotations

import re

import pytest

from camfrog_autodj.config import Config
from camfrog_autodj.exceptions import ConfigError
from camfrog_autodj.theme import THEMES, ZPLAYER_DARK, Theme

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_COLOR_FIELDS = (
    "bg",
    "surface",
    "surface2",
    "border",
    "border_focus",
    "text",
    "muted",
    "inverse",
    "primary",
    "primary_hover",
    "success",
    "warning",
    "danger",
    "on_air",
    "idle",
    "glow",
    "cyan",
)


def test_builtin_palettes_are_complete_and_distinct():
    assert set(THEMES) == {"zplayer-dark", "zplayer-neon", "zplayer-light"}
    for name, palette in THEMES.items():
        assert palette.name == name
        for field in _COLOR_FIELDS:
            assert _HEX.match(getattr(palette, field)), f"{name}.{field} is not a hex colour"
    assert len({palette.bg for palette in THEMES.values()}) == 3


def test_from_name_falls_back_to_dark():
    assert Theme.from_name("zplayer-neon").palette is THEMES["zplayer-neon"]
    assert Theme.from_name("no-such-theme").palette is ZPLAYER_DARK


def test_palette_rebinds_dashboard_colours():
    from camfrog_autodj import gui

    try:
        gui._apply_palette_to_module(THEMES["zplayer-light"])
        assert gui.BG == THEMES["zplayer-light"].bg
        assert gui.TEXT == THEMES["zplayer-light"].text
        assert gui.CYAN == THEMES["zplayer-light"].cyan
    finally:
        gui._apply_palette_to_module(ZPLAYER_DARK)


def test_ui_theme_default_and_config_validation(tmp_path):
    assert Config().ui_theme == "zplayer-dark"

    config_file = tmp_path / "config.toml"
    config_file.write_text('ui_theme = "zplayer-light"\n', encoding="utf-8")
    assert Config.load(str(config_file)).ui_theme == "zplayer-light"

    config_file.write_text('ui_theme = "bogus"\n', encoding="utf-8")
    with pytest.raises(ConfigError, match="ui_theme"):
        Config.load(str(config_file))


def test_welcome_message_delay_range(tmp_path):
    assert Config().welcome_message_delay == 0.0

    config_file = tmp_path / "config.toml"
    config_file.write_text("welcome_message_delay = 2.5\n", encoding="utf-8")
    assert Config.load(str(config_file)).welcome_message_delay == 2.5

    config_file.write_text("welcome_message_delay = 5000\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="welcome_message_delay"):
        Config.load(str(config_file))
