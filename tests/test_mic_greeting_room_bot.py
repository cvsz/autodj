"""Mic greeting when a room bot announces who took the mic.

Live room ZeaZDev: the mic notice is posted by ZeazBot ("Seaza กำลังรับไมค์"),
not by the user who took the mic, so the 0.3.10 rule "sender must be the named
nick" never greeted anyone there.
"""

from __future__ import annotations

from test_core import FakeAdapter, FakePlayer, out

from autodj.adapters.base import ChatMessage
from autodj.config import Config
from autodj.engine import Engine


def _engine(**kw):
    cfg = Config(lang="th", mic_greeting_enabled=True, mic_greeting_cooldown=0, **kw)
    return Engine(cfg, FakeAdapter(), player=FakePlayer(), index=None)


def test_trusted_room_bot_announcement_greets_the_named_user():
    e = _engine(mic_notice_senders=["ZeazBot"])
    e._handle_re_events(ChatMessage("ZeazBot", "zdevz กำลังรับไมค์"))
    assert out(e) == ["คุณ zdevz รับไมค์เป็น DJ ขณะนี้"]


def test_trusted_sender_match_is_case_insensitive():
    e = _engine(mic_notice_senders=["zeazbot"])
    e._handle_re_events(ChatMessage("ZeazBot", "zdevz กำลังรับไมค์"))
    assert out(e) == ["คุณ zdevz รับไมค์เป็น DJ ขณะนี้"]


def test_room_bot_not_listed_is_ignored_by_default():
    e = _engine()  # mic_notice_senders = [] (default)
    e._handle_re_events(ChatMessage("ZeazBot", "zdevz กำลังรับไมค์"))
    assert out(e) == []


def test_ordinary_user_still_cannot_announce_someone_else():
    e = _engine(mic_notice_senders=["ZeazBot"])
    e._handle_re_events(ChatMessage("amy", "zdevz กำลังรับไมค์"))
    assert out(e) == []


def test_ignored_nick_is_not_greeted():
    """The account AutoDJ streams from takes the mic every time music plays."""
    e = _engine(mic_notice_senders=["ZeazBot"], mic_greeting_ignore=["Seaza"])
    e._handle_re_events(ChatMessage("ZeazBot", "Seaza กำลังรับไมค์"))
    e._handle_re_events(ChatMessage("ZeazBot", "seaza กำลังรับไมค์"))
    assert out(e) == []


def test_bot_nick_is_never_greeted():
    e = _engine(mic_notice_senders=["ZeazBot"], bot_nick="AutoDJ")
    e._handle_re_events(ChatMessage("ZeazBot", "AutoDJ กำลังรับไมค์"))
    assert out(e) == []


def test_cooldown_still_applies_to_room_bot_announcements():
    e = _engine(mic_notice_senders=["ZeazBot"])
    e.cfg.mic_greeting_cooldown = 300.0
    e._handle_re_events(ChatMessage("ZeazBot", "zdevz กำลังรับไมค์"))
    e._handle_re_events(ChatMessage("ZeazBot", "zdevz กำลังรับไมค์"))
    assert out(e) == ["คุณ zdevz รับไมค์เป็น DJ ขณะนี้"]


def test_new_keys_in_example_config():
    import tomllib

    with open("config.example.toml", "rb") as fh:
        ex = tomllib.load(fh)
    assert ex["mic_notice_senders"] == [] and ex["mic_greeting_ignore"] == []
    c = Config()
    assert c.mic_notice_senders == [] and c.mic_greeting_ignore == []
