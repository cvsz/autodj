"""Old room commands are never run again when Camfrog changes the last line.

Live 2026-11-25 15:34: a long ZeazBot line was re-rendered (split in two), the last
line of the previous read was no longer in the pane, diff_lines() could not anchor
and returned the whole 300-line buffer. Every `!ขอเพลง` from the last 20 minutes ran
again and songs that had already played were queued again.
"""

from __future__ import annotations

import logging
import re

from autodj.adapters import uia
from autodj.adapters.base import compile_join_rx
from autodj.config import Config


def _adapter() -> uia.UiaAdapter:
    a = uia.UiaAdapter.__new__(uia.UiaAdapter)
    a.cfg = Config()
    a.rx = re.compile(a.cfg.line_regex)
    a.join_rx = compile_join_rx(a.cfg.join_line_regex)
    return a


HISTORY = [
    "15:15 zdevz: !ขอเพลง รักเอย",
    "15:25 zdevz: !ขอเพลง มากกว่ารัก",
    "15:26 zdevz: !ขอเพลง รัก",
    "15:33 zdevz: !ขอเพลง เก็บตะวัน",
    "15:34 ZeazBot: ชีวิตเต็มไปด้วยช่วงเวลาที่ไม่คาดฝัน",
]


def _texts(a, prev, cur):
    return [(m.user, m.text) for m in a._room_events(prev, cur)]


def test_rerendered_last_line_does_not_replay_history(caplog):
    a = _adapter()
    # The last line is now split into two different lines and one new message arrived.
    cur = HISTORY[:-1] + [
        "15:34 ZeazBot: ชีวิตเต็มไปด้วยช่วงเวลาที่ไม่คาดฝัน แต่ทุกความท้าทาย…",
        "15:35 zdevz: !ขอเพลง ใหม่",
    ]
    with caplog.at_level(logging.WARNING, logger="autodj"):
        got = _texts(a, HISTORY, cur)
    assert ("zdevz", "!ขอเพลง ใหม่") in got
    assert all(text != "!ขอเพลง รักเอย" and text != "!ขอเพลง มากกว่ารัก" for _, text in got)
    # 4 old lines dropped; the re-rendered ZeazBot line and the new request get through.
    assert (
        "room history re-read (last seen line changed); 4 old line(s) ignored, 2 new" in caplog.text
    )


def test_older_lines_loaded_above_the_history_are_not_new():
    """Only what follows the last line seen before is new; older lines loaded on top are history."""
    a = _adapter()
    cur = ["15:00 old: hello"] + HISTORY[:-1] + ["15:36 zdevz: !skip"]
    got = _texts(a, HISTORY, cur)
    assert got == [("zdevz", "!skip")]


def test_history_with_no_line_in_common_is_a_new_baseline(caplog):
    """Live 2026-11-27 05:32: the first read was taken while the room page was loading.

    The full history read next shared no line with it, and every old `!ขอเพลง` and
    `!ai` in it ran again (five songs re-queued).
    """
    a = _adapter()
    loading = ["05:31 AutoDJ: กำลังเล่น: Sadwave - EP-0002"]
    with caplog.at_level(logging.WARNING, logger="autodj"):
        events = list(a._room_events(loading, HISTORY))
    assert all(m.event == "seen" for m in events)  # presence only, no command
    assert {m.user for m in events} <= {"zdevz", "ZeazBot"}
    assert "taking it as a new baseline, nothing replayed" in caplog.text


def test_read_failure_still_reads_ims(monkeypatch):
    """A failing room read (not just a hidden room page) must not stop IM reading."""
    from autodj.adapters.base import ChatMessage

    a = _adapter()
    a.com_lock = __import__("threading").RLock()
    a.cfg.poll_interval = 0.0
    calls = {"n": 0}

    def boom():
        calls["n"] += 1
        raise type("COMError", (Exception,), {})("stale element")  # not an OSError

    monkeypatch.setattr(a, "_lines", boom)
    monkeypatch.setattr(a, "_im_lines", lambda: [ChatMessage("amy", "!play x", is_im=True)])
    monkeypatch.setattr(uia.time, "sleep", lambda s: None)
    msg = next(a.messages())
    assert (msg.user, msg.text, msg.is_im) == ("amy", "!play x", True)
    assert calls["n"] == 1


def test_normal_growth_keeps_repeated_commands():
    a = _adapter()
    # Same command again in the same minute is new when the previous last line is still there.
    cur = HISTORY + ["15:34 zdevz: !ขอเพลง เก็บตะวัน"]
    assert _texts(a, HISTORY, cur) == [("zdevz", "!ขอเพลง เก็บตะวัน")]


def test_first_read_is_only_a_baseline():
    a = _adapter()
    assert all(m.event == "seen" for m in a._room_events(None, HISTORY))
