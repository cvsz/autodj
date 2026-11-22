"""Foreground sends wait until nobody is typing on the bot PC.

Live 2026-11-23: the operator typed "ตรวจ ภาษา" on the bot PC while the bot
pasted; "ว", "จ" and "ภาษ...า" were posted glued to the bot's lines.
"""

from __future__ import annotations

import pytest

from autodj.adapters import uia


@pytest.fixture
def clock(monkeypatch):
    t = {"now": 0.0}
    monkeypatch.setattr(uia.time, "monotonic", lambda: t["now"])

    def sleep(s):
        t["now"] += s

    monkeypatch.setattr(uia.time, "sleep", sleep)
    return t


def test_idle_user_is_not_delayed(monkeypatch, clock):
    monkeypatch.setattr(uia, "_idle_seconds", lambda: 60.0)
    uia._wait_user_idle("room")
    assert clock["now"] == 0.0


def test_waits_until_the_user_stops_typing(monkeypatch, clock):
    # typing for 4 s, then idle: idle time counts up from the last keystroke
    monkeypatch.setattr(
        uia, "_idle_seconds", lambda: 0.0 if clock["now"] < 4.0 else clock["now"] - 4.0
    )
    uia._wait_user_idle("room")
    assert 6.0 <= clock["now"] < 8.0  # 4 s typing + 2.5 s idle


def test_types_nothing_while_the_pc_stays_busy(monkeypatch, clock):
    monkeypatch.setattr(uia, "_idle_seconds", lambda: 0.1)
    with pytest.raises(RuntimeError, match="nothing typed"):
        uia._wait_user_idle("room")
    assert clock["now"] >= uia._IDLE_MAX_WAIT_S


def test_unknown_idle_time_never_blocks(monkeypatch):
    import ctypes
    import types

    monkeypatch.setattr(ctypes, "windll", types.SimpleNamespace(), raising=False)
    assert uia._idle_seconds() == float("inf")


def test_send_fg_waits_before_taking_the_focus(monkeypatch):
    calls = []
    monkeypatch.setattr(
        uia,
        "_wait_user_idle",
        lambda what: (
            calls.append(what) or (_ for _ in ()).throw(RuntimeError("busy; nothing typed"))
        ),
    )
    a = uia.UiaAdapter.__new__(uia.UiaAdapter)
    a.win = None  # would crash if anything after the wait ran
    with pytest.raises(RuntimeError, match="nothing typed"):
        a._send_fg("now playing")
    assert calls == ["Camfrog room window"]
