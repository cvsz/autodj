"""Background sends reach the chat editor, not the dialog around it.

Live 2026-11-27 12:56-13:16: every background send was "not confirmed" and, with
someone using the PC, the foreground fallback could not type either, so the bot's
lines were dropped.  The point under the message box is covered by
``#32770 > AtlAxWinLic140 > Shell Embedding > Shell DocObject View >
Internet Explorer_Server``, all exactly the same size; ``pick_child`` kept the
first (the dialog), where ``WM_SETTEXT`` returns TRUE without doing anything.
"""

from __future__ import annotations

import ctypes
from types import SimpleNamespace

from autodj import winmsg
from autodj.adapters import uia

# Handles, nesting order and equal sizes as read from the live window (bg_target_probe.py);
# the coordinates are illustrative (2nd monitor above the primary: y < 0).
_LIVE = [
    (66734, (-6, -1000, 1360, -327)),
    (66752, (-6, -1000, 1360, -327)),
    (66882, (114, -86, 1317, 15)),
    (66910, (114, -86, 1317, -51)),
    (66912, (114, -86, 1317, -51)),
    (66914, (114, -86, 1317, -51)),
    (66918, (114, -86, 1317, -51)),
    (66946, (114, -86, 1317, -51)),
]


def test_pick_child_tie_prefers_the_deepest_window():
    assert winmsg.pick_child(_LIVE, (715, -62)) == 66946


def test_pick_child_still_prefers_the_smallest():
    rects = [(1, (0, 0, 100, 100)), (2, (0, 0, 50, 50)), (3, (0, 0, 100, 100))]
    assert winmsg.pick_child(rects, (10, 10)) == 2


def _adapter(posted, value_ok=True):
    a = uia.UiaAdapter.__new__(uia.UiaAdapter)
    a.win = SimpleNamespace(handle=131720)
    host = SimpleNamespace(handle=66946, parent=None)
    inp = SimpleNamespace(
        rectangle=lambda: SimpleNamespace(left=121, top=-79, right=1310, bottom=-44),
        element_info=SimpleNamespace(handle=None, parent=host),
        iface=SimpleNamespace(CurrentIsEnabled=True),
        iface_value=SimpleNamespace(
            CurrentIsReadOnly=not value_ok, SetValue=lambda t: posted.append(("setvalue", t))
        ),
    )
    a._input = inp
    return a


def _patch(monkeypatch, posted, rich_ok=True):
    monkeypatch.setattr(winmsg, "show_noactivate", lambda h: None)

    def rich(top, pt, text, enter=True, click=True, target=None):
        posted.append(("rich", target))
        return rich_ok

    def chars(top, pt, text, enter=True, click=True, delay=0.004, target=None):
        posted.append(("chars" if text else "enter", target))
        return True

    monkeypatch.setattr(winmsg, "post_text_rich", rich)
    monkeypatch.setattr(winmsg, "post_text", chars)
    fake = SimpleNamespace(user32=SimpleNamespace(IsChild=lambda top, h: top == 131720))
    monkeypatch.setattr(ctypes, "windll", fake, raising=False)


def test_send_goes_to_the_uia_host_window(monkeypatch):
    posted: list = []
    _patch(monkeypatch, posted)
    a = _adapter(posted)
    assert a._send_bg("hi", 1)
    assert posted == [("chars", 66946)]


def test_second_attempt_starts_with_another_strategy(monkeypatch):
    posted: list = []
    _patch(monkeypatch, posted)
    a = _adapter(posted)
    assert a._send_bg("hi", 2)
    assert posted == [("rich", 66946)]
    posted.clear()
    assert a._send_bg("hi", 3)
    assert posted == [("setvalue", "hi"), ("enter", 66946)]


def test_falls_through_when_a_strategy_reports_failure(monkeypatch):
    posted: list = []
    _patch(monkeypatch, posted, rich_ok=False)
    a = _adapter(posted, value_ok=False)  # read-only: SetValue is skipped
    assert a._send_bg("hi", 2)
    assert posted == [("rich", 66946), ("chars", 66946)]


class NoPatternInterfaceError(Exception):  # pywinauto's, not an OSError/RuntimeError
    pass


def test_missing_value_pattern_does_not_abort_the_send(monkeypatch):
    posted: list = []
    _patch(monkeypatch, posted)
    a = _adapter(posted)

    class _NoValue:
        @property
        def iface_value(self):
            raise NoPatternInterfaceError()

    no_value = _NoValue()
    no_value.rectangle = a._input.rectangle
    no_value.element_info = a._input.element_info
    a._input = no_value
    assert a._send_bg("hi", 3)  # starts at SetValue, which raises
    assert posted == [("chars", 66946)]


def test_host_outside_the_room_window_is_not_used(monkeypatch):
    posted: list = []
    _patch(monkeypatch, posted)
    monkeypatch.setattr(
        ctypes,
        "windll",
        SimpleNamespace(user32=SimpleNamespace(IsChild=lambda t, h: False)),
        raising=False,
    )
    a = _adapter(posted)
    assert a._input_host(131720) is None
    assert a._send_bg("hi", 1)
    assert posted == [("chars", None)]  # winmsg falls back to pick_child
