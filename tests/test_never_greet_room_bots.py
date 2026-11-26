"""Room bots are never greeted by any greeting.

Live 2026-11-23..27 (room ZeazDev): "Sent welcome message to ZeazBot" five times;
the operator asked that the room's bots (ZeazBot, CloudBot, ...) are never greeted.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from test_core import FakeAdapter, FakePlayer, out

from autodj.adapters.base import ChatMessage
from autodj.config import Config, ConfigError
from autodj.engine import Engine


def _engine(**kw):
    cfg = Config(
        lang="th",
        welcome_message_enabled=True,
        welcome_message_cooldown=0,
        mic_greeting_enabled=True,
        mic_greeting_cooldown=0,
        mic_notice_senders=["ZeazBot"],
        admins=["zdevz", "CloudBot"],
        **kw,
    )
    return Engine(cfg, FakeAdapter(), player=FakePlayer(), index=None)


@pytest.mark.parametrize("nick", ["ZeazBot", "CloudBot", "cloudbot", "CamfrogBot"])
def test_bot_nicks_get_no_welcome_by_default(nick):
    e = _engine()
    assert e._greet_user(nick) is False
    assert e._handle_welcome_message(ChatMessage(nick, "")) is False
    assert out(e) == []


def test_admin_bot_gets_no_admin_greeting():
    e = _engine()
    assert e._handle_admin_greeting(ChatMessage("CloudBot", "")) is False
    assert out(e) == []


def test_mic_greeting_skips_room_bots():
    e = _engine()
    e._handle_re_events(ChatMessage("ZeazBot", "CloudBot กำลังรับไมค์"))
    assert out(e) == []


def test_real_users_are_still_greeted():
    e = _engine()
    assert e._greet_user("amy") is True
    e._handle_re_events(ChatMessage("ZeazBot", "zdevz กำลังรับไมค์"))
    texts = out(e)
    assert any("amy" in t for t in texts)
    assert "คุณ zdevz รับไมค์เป็น DJ ขณะนี้" in texts


def test_greeting_ignore_list_covers_every_greeting():
    e = _engine(greeting_ignore=["Mod1"], greeting_ignore_regex="")
    assert e._greet_user("mod1") is False
    e._handle_re_events(ChatMessage("ZeazBot", "Mod1 กำลังรับไมค์"))
    assert out(e) == []


def test_mic_greeting_ignore_now_blocks_the_welcome_too():
    e = _engine(mic_greeting_ignore=["Streamer"], greeting_ignore_regex="")
    assert e._greet_user("Streamer") is False


def test_regex_can_be_turned_off():
    e = _engine(greeting_ignore_regex="")
    assert e._greet_user("ZeazBot") is True


def test_invalid_regex_fails_config_load(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text('greeting_ignore_regex = "(unclosed"\n', encoding="utf-8")
    with pytest.raises(ConfigError):
        Config.load(str(p))


def test_example_config_documents_the_keys():
    data = tomllib.loads(
        (Path(__file__).resolve().parent.parent / "config.example.toml").read_text(encoding="utf-8")
    )
    assert data["greeting_ignore"] == []
    assert data["greeting_ignore_regex"] == "(?i)bot$"
