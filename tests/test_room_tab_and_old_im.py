"""Room tab re-selected when the PC is idle; old private messages are not replayed.

Live 2026-11-27 12:50-12:56: the window was switched to the room list and the bot
read nothing (no IM reached the IM tab) until the room tab was clicked; then
Camfrog re-rendered the 12:19 private messages at the end of the history.
"""

from __future__ import annotations

import re
import time
from types import SimpleNamespace

from autodj.adapters import uia
from autodj.adapters.base import compile_join_rx
from autodj.config import Config


def _adapter() -> uia.UiaAdapter:
    a = uia.UiaAdapter.__new__(uia.UiaAdapter)
    a.cfg = Config(room="ZeaZDev")
    a.rx = re.compile(a.cfg.line_regex)
    a.join_rx = compile_join_rx(a.cfg.join_line_regex)
    return a


class _Btn:
    def __init__(self, name, cls, handle):
        self.element_info = SimpleNamespace(name=name, class_name=cls, handle=handle)


def _with_buttons(a, posted):
    a.win = SimpleNamespace(
        descendants=lambda control_type=None: [
            _Btn("รายชื่อห้อง", "CButtonTS", 11),
            _Btn("ZeaZDev", "CButtonTS", 22),
        ]
    )
    import ctypes

    fake = SimpleNamespace(user32=SimpleNamespace(PostMessageW=lambda *a: posted.append(a)))
    return ctypes, fake


def test_room_tab_is_clicked_after_the_delay_when_idle(monkeypatch):
    a = _adapter()
    posted: list = []
    ctypes, fake = _with_buttons(a, posted)
    monkeypatch.setattr(ctypes, "windll", fake, raising=False)
    monkeypatch.setattr(uia, "_idle_seconds", lambda: 600.0)
    now = time.monotonic()
    a._hidden_since = now
    a._maybe_reselect_room_tab(now + 10)  # too early
    assert posted == []
    a._maybe_reselect_room_tab(now + a.ROOM_TAB_RESELECT_S + 1)
    assert posted == [(22, 0x00F5, 0, 0)]  # BM_CLICK on the ZeaZDev tab button
    a._maybe_reselect_room_tab(now + a.ROOM_TAB_RESELECT_S + 2)
    assert len(posted) == 1  # throttled


def test_room_tab_is_left_alone_while_someone_uses_the_pc(monkeypatch):
    a = _adapter()
    posted: list = []
    ctypes, fake = _with_buttons(a, posted)
    monkeypatch.setattr(ctypes, "windll", fake, raising=False)
    monkeypatch.setattr(uia, "_idle_seconds", lambda: 2.0)
    a._hidden_since = time.monotonic() - 3600
    a._maybe_reselect_room_tab(time.monotonic())
    assert posted == []


def test_old_private_message_from_a_rerender_is_not_delivered(monkeypatch):
    a = _adapter()
    lt = time.localtime()
    now_s = f"{lt.tm_hour}:{lt.tm_min:02d}"
    old = time.localtime(time.time() - 3600)
    old_s = f"{old.tm_hour}:{old.tm_min:02d}"
    prev = [f"{now_s} zdevz: hello"]
    cur = prev + [f"{old_s} IM amy: !play old song", f"{now_s} IM amy: !play new song"]
    got = [(m.user, m.text, m.is_im) for m in a._room_events(prev, cur)]
    assert got == [("amy", "!play new song", True)]


def test_room_lines_are_not_age_filtered():
    a = _adapter()
    old = time.localtime(time.time() - 3600)
    old_s = f"{old.tm_hour}:{old.tm_min:02d}"
    prev = ["1:00 zdevz: hello"]
    cur = prev + [f"{old_s} zdevz: !skip"]
    assert [(m.user, m.text) for m in a._room_events(prev, cur)] == [("zdevz", "!skip")]
