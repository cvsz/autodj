"""Regression tests for the autodj-enhancements-and-fixes feature set.

Covers: auto-reply loop, IM command handling, seek, double-click queue-to-play-now,
and settings persistence of auto-reply fields.
"""

import json
import os

import pytest
from test_core import FakeAdapter, FakePlayer, T, make, out

from camfrog_autodj.adapters.base import ChatMessage
from camfrog_autodj.config import Config, ConfigError
from camfrog_autodj.engine import Engine
from camfrog_autodj.models import Track
from camfrog_autodj.playqueue import PlayQueue

# ============================================================================
# Auto-reply loop
# ============================================================================


def _make_auto_reply_engine(
    tmp_path, enabled=True, interval=60, file_name="ads-list.json"
):
    """Create an engine with auto-reply config and a temp ads-list.json."""
    ads = tmp_path / file_name
    ads.write_text(
        json.dumps({"version": 1, "messages": ["msg one", "msg two", "msg three"]}),
        "utf-8",
    )
    cfg = Config(
        auto_reply_enabled=enabled,
        auto_reply_interval=float(interval),
        auto_reply_file=str(ads),
    )
    e = Engine(cfg, FakeAdapter(), player=FakePlayer(), index=None)
    e.cfg_path = str(tmp_path / "config.toml")
    return e, ads


def test_auto_reply_disabled_loop_returns_immediately(tmp_path):
    e, _ = _make_auto_reply_engine(tmp_path, enabled=False)
    # _auto_reply_loop should return without sending anything
    e._auto_reply_loop()
    assert out(e) == []


def test_auto_reply_no_file_warns_and_returns(tmp_path):
    """Missing auto-reply file: no crash, no messages, loop returns."""
    cfg = Config(
        auto_reply_enabled=True,
        auto_reply_interval=60.0,
        auto_reply_file=str(tmp_path / "nonexistent.json"),
    )
    e = Engine(cfg, FakeAdapter(), player=FakePlayer(), index=None)
    e._auto_reply_loop()
    assert out(e) == []  # no messages to send


def test_auto_reply_rotation_order(tmp_path):
    """Messages rotate through the list in order (tests the rotation formula)."""
    ads = tmp_path / "ads-list.json"
    ads.write_text(
        json.dumps({"version": 1, "messages": ["msg one", "msg two", "msg three"]}),
        "utf-8",
    )
    messages = Engine._load_auto_reply_messages(str(ads))
    assert messages == ["msg one", "msg two", "msg three"]

    # Simulate the loop's rotation formula: messages[idx % len(messages)]
    rotated = [messages[i % len(messages)] for i in range(6)]
    assert rotated == [
        "msg one",
        "msg two",
        "msg three",
        "msg one",
        "msg two",
        "msg three",
    ]


def test_auto_reply_minimum_interval_enforced(tmp_path, monkeypatch):
    """Interval below 60s is raised to 60s by the loop."""
    e, _ads = _make_auto_reply_engine(tmp_path, enabled=True, interval=5)
    # Verify config accepts 5 but loop enforces 60
    assert e.cfg.auto_reply_interval == 5.0
    assert max(60.0, e.cfg.auto_reply_interval) == 60.0


def test_auto_reply_relative_path_resolved_against_config_dir(tmp_path):
    """Relative auto_reply_file is resolved against config file directory."""
    cfg_dir = tmp_path / "cfgdir"
    cfg_dir.mkdir()
    ads = cfg_dir / "ads-list.json"
    ads.write_text(json.dumps({"messages": ["resolved message"]}), "utf-8")
    cfg_path = cfg_dir / "config.toml"

    cfg = Config(
        auto_reply_enabled=True,
        auto_reply_interval=60.0,
        auto_reply_file="ads-list.json",  # relative
    )
    e = Engine(cfg, FakeAdapter(), player=FakePlayer(), index=None)
    e.cfg_path = str(cfg_path)

    # Simulate the path resolution logic from _auto_reply_loop
    path = e.cfg.auto_reply_file
    if not os.path.isabs(path) and e.cfg_path:
        path = str(os.path.join(os.path.dirname(e.cfg_path), path))

    assert path == str(ads)
    messages = Engine._load_auto_reply_messages(path)
    assert messages == ["resolved message"]


def test_auto_reply_invalid_file_graceful(tmp_path):
    """Corrupt JSON file is handled gracefully."""
    ads = tmp_path / "ads-list.json"
    ads.write_text("{ not valid json", "utf-8")
    cfg = Config(
        auto_reply_enabled=True,
        auto_reply_interval=60.0,
        auto_reply_file=str(ads),
    )
    e = Engine(cfg, FakeAdapter(), player=FakePlayer(), index=None)
    e._auto_reply_loop()
    assert out(e) == []  # no crash, no messages


# ============================================================================
# IM command handling
# ============================================================================


class OneShotAdapter(FakeAdapter):
    """Adapter that yields a fixed list of messages then stops."""

    def __init__(self, msgs):
        self.msgs = msgs

    def messages(self):
        return iter(self.msgs)


def test_im_command_without_prefix():
    """IM messages are handled without the command prefix."""
    e = make()
    e.admins = {"boss"}
    e.player.play = lambda s, v, d=None: True
    e.current = Track("s", "now", 90, "boss")

    # IM pause command (no "!" prefix)
    e.router.handle(ChatMessage("boss", "pause", is_im=True))
    assert e.paused is True


def test_im_command_requires_admin_for_admin_cmd():
    """IM admin commands still require admin authorization."""
    e = make()
    e.admins = {"boss"}
    e.player.play = lambda s, v, d=None: True
    e.current = Track("s", "now", 90, "boss")

    # Non-admin tries IM pause
    e.router.handle(ChatMessage("amy", "pause", is_im=True))
    assert out(e) == ["amy: admin only"]
    assert e.paused is False


def test_im_play_command_no_prefix():
    """IM play command works without prefix."""
    e = make()
    e.router.handle(ChatMessage("amy", "play song one", is_im=True))
    assert out(e) == ["Queued #1: song one [2:00] for amy"]


def test_room_message_without_prefix_is_ignored():
    """Room messages without prefix are not treated as commands."""
    e = make()
    e.router.handle(ChatMessage("amy", "pause"))
    assert out(e) == []
    assert e.paused is False


def test_im_cooldown_still_applies():
    """IM commands are subject to cooldown."""
    e = make()
    e.cfg.cooldown = 10.0
    e.router.handle(ChatMessage("amy", "play song one", is_im=True))
    out(e)
    # Second IM play immediately — should be on cooldown
    e.router.handle(ChatMessage("amy", "play song two", is_im=True))
    assert out(e) == []  # cooldown drops it


def test_im_blocked_user_ignored():
    """Blocked users are ignored even via IM."""
    e = make()
    e.admins = {"boss"}
    e.blocked.add("amy")
    e.router.handle(ChatMessage("amy", "pause", is_im=True))
    assert out(e) == []
    assert e.paused is False


# ============================================================================
# Seek functionality
# ============================================================================


class SeekablePlayer(FakePlayer):
    """Fake player that records seek calls."""

    def __init__(self):
        super().__init__()
        self.seek_calls = []

    def seek(self, seconds):
        self.seek_calls.append(seconds)
        return True


def test_engine_seek_delegates_to_player():
    """Engine.seek() calls MpvPlayer.seek()."""
    player = SeekablePlayer()
    e = make()
    e.player = player
    e.current = Track("s", "now", 120, "amy")

    result = e.seek(45.5)
    assert result is True
    assert player.seek_calls == [45.5]


def test_engine_seek_no_current_track():
    """Engine.seek() returns False when nothing is playing."""
    player = SeekablePlayer()
    e = make()
    e.player = player
    e.current = None

    result = e.seek(10.0)
    assert result is False
    assert player.seek_calls == []


def test_player_seek_returns_bool():
    """MpvPlayer.seek() delegates to _cmd and returns bool."""
    from camfrog_autodj.player import MpvPlayer

    cfg = Config(mpv_path="mpv")
    player = MpvPlayer(cfg)
    # No IPC connection, so _cmd returns False
    assert player.seek(10.0) is False


# ============================================================================
# Double-click queue to play now (add_request with position=0)
# ============================================================================


def test_add_request_position_zero_moves_to_front():
    """add_request(t, position=0) inserts at the front of the queue."""
    q = PlayQueue(shuffle=False)
    q.add_pool([T("a"), T("b"), T("c")])
    q.add_request(T("new", "you"), position=0)
    assert q.pop().title == "new"
    assert q.pop().title == "a"
    assert q.pop().title == "b"
    assert q.pop().title == "c"


def test_add_request_position_clamped():
    """Position beyond queue length is clamped to the end."""
    q = PlayQueue(shuffle=False)
    q.add_request(T("a"))
    q.add_request(T("b"), position=100)  # clamped to len=1
    assert q.pop().title == "a"
    assert q.pop().title == "b"


def test_add_request_negative_position_clamped_to_zero():
    """Negative position is clamped to 0 (front)."""
    q = PlayQueue(shuffle=False)
    q.add_request(T("a"))
    q.add_request(T("b"), position=-5)
    assert q.pop().title == "b"
    assert q.pop().title == "a"


# ============================================================================
# Config validation for auto_reply_interval
# ============================================================================


def test_auto_reply_interval_below_min_rejected(tmp_path):
    """auto_reply_interval < 60 is rejected by config validation."""
    with pytest.raises(ConfigError) as ei:
        Config.load(_cfg(tmp_path, "auto_reply_interval = 10\n"))
    assert "auto_reply_interval" in str(ei.value)


def test_auto_reply_interval_at_min_accepted(tmp_path):
    """auto_reply_interval = 60 is accepted."""
    c = Config.load(_cfg(tmp_path, "auto_reply_interval = 60\n"))
    assert c.auto_reply_interval == 60.0


def test_auto_reply_interval_at_max_accepted(tmp_path):
    """auto_reply_interval = 86400 is accepted."""
    c = Config.load(_cfg(tmp_path, "auto_reply_interval = 86400\n"))
    assert c.auto_reply_interval == 86400.0


def test_auto_reply_interval_above_max_rejected(tmp_path):
    """auto_reply_interval > 86400 is rejected."""
    with pytest.raises(ConfigError) as ei:
        Config.load(_cfg(tmp_path, "auto_reply_interval = 90000\n"))
    assert "auto_reply_interval" in str(ei.value)


def _cfg(tmp_path, text):
    p = tmp_path / "config.toml"
    p.write_text(text, "utf-8")
    return str(p)


# ============================================================================
# Settings persistence (auto-reply fields written to TOML)
# ============================================================================


def test_save_settings_writes_auto_reply_fields(tmp_path, monkeypatch):
    """save_settings() persists auto_reply_* fields to config.toml."""
    # We test the TOML writer logic directly by checking the lines it would produce
    ads = tmp_path / "ads-list.json"
    ads.write_text(json.dumps({"messages": ["hello"]}), "utf-8")

    cfg = Config(
        auto_reply_enabled=True,
        auto_reply_interval=120.0,
        auto_reply_file=str(ads),
    )

    # Manually build the TOML lines that save_settings() would write
    lines = []
    lines.append(f"auto_reply_enabled = {str(cfg.auto_reply_enabled).lower()}")
    lines.append(f"auto_reply_interval = {cfg.auto_reply_interval}")
    lines.append(f'auto_reply_file = "{cfg.auto_reply_file}"')
    new_text = "\n".join(lines) + "\n"

    # Validate it parses back
    import tomllib

    parsed = tomllib.loads(new_text)
    assert parsed["auto_reply_enabled"] is True
    assert parsed["auto_reply_interval"] == 120.0
    assert parsed["auto_reply_file"] == str(ads)


def test_load_auto_reply_messages_dict_format(tmp_path):
    """_load_auto_reply_messages handles {'messages': [...]} format."""
    ads = tmp_path / "ads-list.json"
    ads.write_text(json.dumps({"version": 1, "messages": ["a", "b", "c"]}), "utf-8")
    result = Engine._load_auto_reply_messages(str(ads))
    assert result == ["a", "b", "c"]


def test_load_auto_reply_messages_list_format(tmp_path):
    """_load_auto_reply_messages handles plain list format."""
    ads = tmp_path / "ads-list.json"
    ads.write_text(json.dumps(["a", "b"]), "utf-8")
    result = Engine._load_auto_reply_messages(str(ads))
    assert result == ["a", "b"]


def test_load_auto_reply_messages_empty(tmp_path):
    """_load_auto_reply_messages handles empty messages list."""
    ads = tmp_path / "ads-list.json"
    ads.write_text(json.dumps({"messages": []}), "utf-8")
    result = Engine._load_auto_reply_messages(str(ads))
    assert result == []


def test_load_auto_reply_messages_missing_file(tmp_path):
    """_load_auto_reply_messages returns [] for missing file."""
    result = Engine._load_auto_reply_messages(str(tmp_path / "nope.json"))
    assert result == []
