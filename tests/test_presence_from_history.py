"""After a restart, users already in the room are known from the visible history."""

import re
import time

from autodj.adapters import NullAdapter
from autodj.adapters.base import ChatMessage
from autodj.adapters.uia import UiaAdapter
from autodj.config import Config
from autodj.engine import Engine


def _adapter():
    cfg = Config()
    a = UiaAdapter.__new__(UiaAdapter)
    a.cfg = cfg
    a.rx = re.compile(cfg.line_regex)
    from autodj.adapters.base import compile_join_rx

    a.join_rx = compile_join_rx(cfg.join_line_regex)
    return a


def _hm(seconds_ago: float) -> str:
    t = time.localtime(time.time() - seconds_ago)
    return f"{t.tm_hour}:{t.tm_min:02d}"


def test_recent_speakers_are_seen_old_ones_are_not():
    a = _adapter()
    lines = [
        f"{_hm(5 * 3600)} oldguy: hello from long ago",
        f"{_hm(600)} zdevz: !ขอเพลง รักครั้งแรก",
        f"{_hm(60)} ZeazBot: quote of the day",
    ]
    nicks = a._recent_nicks(lines)
    assert "zdevz" in nicks and "ZeazBot" in nicks and "oldguy" not in nicks


def test_seen_event_marks_presence_without_greeting():
    e = Engine(Config(room="ZeaZDev", welcome_message_enabled=True), NullAdapter())
    said: list[str] = []
    e.say = lambda text, *a, **k: said.append(text) or True  # type: ignore[method-assign]
    e.adapter.messages = lambda: iter([ChatMessage("zdevz", "", event="seen")])  # type: ignore[method-assign]
    e._chat_loop()
    assert "zdevz" in e._active_room_users
    assert said == []  # no welcome, no reply


def test_im_reply_echo_with_join_link_is_ignored():
    e = Engine(Config(room="ZeaZDev"), NullAdapter())
    e.adapter.send_im = lambda user, text: None  # type: ignore[attr-defined]
    e.send_im("zdevz", "กรุณาเข้าห้อง camfrog:join:ZeaZDev ก่อนขอเพลงครับ")
    assert e._is_echo("กรุณาเข้าห้อง")  # what the IM reader gets back (text before the link)
