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


def test_replaced_buffer_yields_only_lines_not_seen_before():
    a = _adapter()
    cur = ["15:00 old: hello"] + HISTORY[:-1] + ["15:36 zdevz: !skip"]
    got = _texts(a, HISTORY, cur)
    assert got == [("old", "hello"), ("zdevz", "!skip")]


def test_normal_growth_keeps_repeated_commands():
    a = _adapter()
    # Same command again in the same minute is new when the previous last line is still there.
    cur = HISTORY + ["15:34 zdevz: !ขอเพลง เก็บตะวัน"]
    assert _texts(a, HISTORY, cur) == [("zdevz", "!ขอเพลง เก็บตะวัน")]


def test_first_read_is_only_a_baseline():
    a = _adapter()
    assert all(m.event == "seen" for m in a._room_events(None, HISTORY))
