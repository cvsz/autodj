"""Room foreground send must never type into another application.

Live 2026-11-22: Windows refused to give Camfrog the focus while the user worked
in a terminal running a coding agent; _send_fg clicked + pasted + pressed Enter
anyway, so the bot's room announcements went into that terminal, and the
verification still logged "send ok" because an identical auto-reply was in the
room history.
"""

from __future__ import annotations

import ctypes
import sys
import types

import pytest

from autodj.adapters import uia
from autodj.config import Config

ROOM = 1001
OTHER = 2002


class _User32:
    """Fake user32: *front* is the foreground window; *root_at_point* owns the click point."""

    def __init__(self, front=OTHER, can_focus=False, root_at_point=ROOM):
        self.front = front
        self.can_focus = can_focus
        self.root_at_point = root_at_point

    def IsIconic(self, h):
        return False

    def ShowWindow(self, h, n):
        return True

    def BringWindowToTop(self, h):
        return True

    def SetForegroundWindow(self, h):
        if self.can_focus:
            self.front = h
        return self.can_focus

    def GetForegroundWindow(self):
        return self.front

    def WindowFromPoint(self, pt):
        return 7

    def GetAncestor(self, h, flag):
        return self.root_at_point


@pytest.fixture
def user32(monkeypatch):
    fake = _User32()
    monkeypatch.setattr(ctypes, "windll", types.SimpleNamespace(user32=fake), raising=False)
    monkeypatch.setattr(uia.time, "sleep", lambda s: None)
    return fake


def test_focus_refused_types_nothing(user32):
    user32.can_focus = False
    with pytest.raises(RuntimeError, match="could not be brought to the front"):
        uia._focus_target(ROOM, 10, 10, "Camfrog room window")


def test_covered_message_box_types_nothing(user32):
    user32.can_focus = True
    user32.root_at_point = OTHER  # a terminal window covers the message box
    with pytest.raises(RuntimeError, match="covered by another window"):
        uia._focus_target(ROOM, 10, 10, "Camfrog room window")


def test_focus_ok_when_front_and_uncovered(user32):
    user32.can_focus = True
    uia._focus_target(ROOM, 10, 10, "Camfrog room window")
    assert user32.front == ROOM


def _adapter_for_fg(monkeypatch, keys: list[str]):
    """UiaAdapter with fake window/input and fake pyperclip/pywinauto modules."""
    clip = {"v": "user clipboard"}
    monkeypatch.setitem(
        sys.modules,
        "pyperclip",
        types.SimpleNamespace(
            paste=lambda: clip["v"],
            copy=lambda v: clip.__setitem__("v", v),
            PyperclipException=Exception,
        ),
    )
    kb = types.ModuleType("pywinauto.keyboard")
    kb.send_keys = lambda k, **kw: keys.append(k)
    monkeypatch.setitem(sys.modules, "pywinauto", types.ModuleType("pywinauto"))
    monkeypatch.setitem(sys.modules, "pywinauto.keyboard", kb)
    from autodj import winmsg

    monkeypatch.setattr(winmsg, "foreground", lambda: OTHER)
    monkeypatch.setattr(winmsg, "restore_foreground", lambda h: None)

    a = uia.UiaAdapter.__new__(uia.UiaAdapter)
    a.cfg = Config()
    a._web = True
    rect = types.SimpleNamespace(left=0, top=0, right=20, bottom=20)
    a._input = types.SimpleNamespace(rectangle=lambda: rect, click_input=lambda: None)
    a.win = types.SimpleNamespace(
        handle=ROOM, is_minimized=lambda: False, restore=lambda: None, set_focus=lambda: None
    )
    return a, clip


def test_send_fg_never_presses_keys_when_focus_is_refused(user32, monkeypatch):
    keys: list[str] = []
    a, clip = _adapter_for_fg(monkeypatch, keys)
    user32.can_focus = False
    with pytest.raises(RuntimeError):
        a._send_fg("now playing")
    assert keys == []  # no Ctrl+V, no Enter into the other app
    assert clip["v"] == "user clipboard"


def test_send_fg_no_enter_if_focus_lost_after_paste(user32, monkeypatch):
    keys: list[str] = []
    a, _ = _adapter_for_fg(monkeypatch, keys)
    user32.can_focus = True

    def paste_then_lose_focus(k, **kw):
        keys.append(k)
        if k == "^v":
            user32.front = OTHER  # another app grabbed the focus

    sys.modules["pywinauto.keyboard"].send_keys = paste_then_lose_focus
    with pytest.raises(RuntimeError, match="lost the focus"):
        a._send_fg("now playing")
    assert "{ENTER}" not in keys


def test_send_fg_happy_path_pastes_and_enters(user32, monkeypatch):
    keys: list[str] = []
    a, clip = _adapter_for_fg(monkeypatch, keys)
    user32.can_focus = True
    a._send_fg("now playing")
    assert keys == ["^v", "{ENTER}"]
    assert clip["v"] == "user clipboard"  # restored


def test_appeared_ignores_identical_older_line(monkeypatch):
    """An auto-reply already in the history must not confirm a new send."""
    monkeypatch.setattr(uia.time, "sleep", lambda s: None)
    times = iter([0.0, 1.0, 2.0, 3.0, 4.0, 99.0, 99.0])
    monkeypatch.setattr(uia.time, "time", lambda: next(times))
    a = uia.UiaAdapter.__new__(uia.UiaAdapter)
    a.cfg = Config(bot_nick="AutoDJ")
    history = ["1:37|Seaza: ขอบคุณที่เข้ามาฟังเพลง", "3:20|ZeazBot: hello"]
    a._lines = lambda: list(history)  # nothing new arrives
    assert a._appeared("ขอบคุณที่เข้ามาฟังเพลง", history) is False


def test_appeared_sees_the_new_line(monkeypatch):
    monkeypatch.setattr(uia.time, "sleep", lambda s: None)
    a = uia.UiaAdapter.__new__(uia.UiaAdapter)
    a.cfg = Config(bot_nick="AutoDJ")
    history = ["1:37|Seaza: ขอบคุณที่เข้ามาฟังเพลง"]
    a._lines = lambda: history + ["3:25|Seaza: ขอบคุณที่เข้ามาฟังเพลง"]
    assert a._appeared("ขอบคุณที่เข้ามาฟังเพลง", history) is True


def test_send_fg_waits_for_webview_focus_before_paste(user32, monkeypatch):
    """Live 2026-11-22: 0.2 s after the click the WebView2 editor had no focus yet, the
    Ctrl+V was lost and only Enter arrived (empty send, or a leftover draft posted)."""
    events: list[tuple[str, object]] = []
    a, clip = _adapter_for_fg(monkeypatch, [])
    user32.can_focus = True
    a._input.click_input = lambda: events.append(("click", clip["v"]))
    monkeypatch.setattr(uia.time, "sleep", lambda s: events.append(("sleep", s)))
    sys.modules["pywinauto.keyboard"].send_keys = lambda k, **kw: events.append(("key", k))
    a._send_fg("now playing")
    click = events.index(("click", "now playing"))  # clipboard already holds the text
    paste = events.index(("key", "^v"))
    enter = events.index(("key", "{ENTER}"))
    waited = sum(s for kind, s in events[click:paste] if kind == "sleep")
    assert waited >= 0.35
    assert sum(s for kind, s in events[paste:enter] if kind == "sleep") >= 0.25
