"""A new IM window whose chat pane loads late is read once the pane exists.

Live 2026-11-27: no IM ever reached the IM tab. A Camfrog chat window appears
before its web pane has loaded; the first read found no pane and the window was
put on the "not an IM window" list for good, so that chat was never read again.
"""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace

import autodj.windows as windows
from autodj.adapters import uia


def _adapter(monkeypatch, wins):
    a = uia.UiaAdapter.__new__(uia.UiaAdapter)
    a.cfg = SimpleNamespace(process_re="")
    a.handle = 100
    a.com_lock = threading.RLock()
    monkeypatch.setattr(windows, "candidates", lambda *a, **k: wins)
    return a


def test_window_without_pane_is_checked_again_later(monkeypatch):
    wins = [SimpleNamespace(handle=300, pid=2, title="Bob (IM)")]
    a = _adapter(monkeypatch, wins)
    a._im_lines()  # first scan: baseline, nothing open yet
    pane: list = []  # empty -> the pane has not loaded
    stamp = time.strftime("%H:%M")

    def read(win):
        return ([f"{stamp}|!ขอเพลง test"], "Bob") if pane else None

    monkeypatch.setattr(a, "_read_im_window", read)
    assert a._im_lines() == []  # window just opened, pane still loading
    pane.append(True)
    assert a._im_lines() == []  # within the recheck delay: not read yet
    a._im_not_im[300] = time.monotonic() - 1  # recheck delay elapsed
    got = a._im_lines()
    assert [(m.user, m.text, m.is_im) for m in got] == [("Bob", "!ขอเพลง test", True)]


def test_closed_windows_are_forgotten(monkeypatch):
    wins = [SimpleNamespace(handle=300, pid=2, title="popup")]
    a = _adapter(monkeypatch, wins)
    monkeypatch.setattr(a, "_read_im_window", lambda win: None)
    a._im_lines()
    assert 300 in a._im_not_im
    wins.clear()
    a._im_lines()
    assert a._im_not_im == {}
