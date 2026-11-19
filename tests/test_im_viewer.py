"""IM viewer path: Camfrog IM pane -> UiaAdapter -> Engine.im_log -> GUI snapshot.

Regressions from a live Camfrog test: the first message of a new chat window
was swallowed as "baseline", and windows without an IM pane were re-scanned
(and logged) on every poll.
"""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace

from autodj.adapters import NullAdapter, uia
from autodj.adapters.base import ChatMessage
from autodj.config import Config
from autodj.engine import Engine


def _stamp(offset_s: float = 0.0) -> str:
    return time.strftime("%H:%M", time.localtime(time.time() - offset_s))


def _adapter(monkeypatch, panes: dict[int, list[str] | None], wins):
    a = uia.UiaAdapter.__new__(uia.UiaAdapter)
    a.cfg = SimpleNamespace(process_re="")
    a.handle = 1
    a.com_lock = threading.RLock()
    import autodj.windows as w

    monkeypatch.setattr(w, "candidates", lambda *a_, **k: wins)
    reads: list[int] = []

    def read(win):
        reads.append(win.handle)
        lines = panes.get(win.handle)
        return None if lines is None else (lines, win.title.split(" (", 1)[0])

    monkeypatch.setattr(a, "_read_im_window", read)
    return a, reads


def test_is_recent():
    now = time.time()
    assert uia.UiaAdapter._is_recent(_stamp(), now)
    assert not uia.UiaAdapter._is_recent(_stamp(3600), now)
    assert not uia.UiaAdapter._is_recent("bogus", now)


def test_first_message_of_a_new_chat_window_is_delivered(monkeypatch):
    panes: dict[int, list[str] | None] = {10: [f"{_stamp(7200)}|old history"]}
    wins = [SimpleNamespace(handle=10, pid=2, title="amy (IM)")]
    a, _reads = _adapter(monkeypatch, panes, wins)
    assert a._im_lines() == []  # startup: existing window is a baseline
    # zdevz opens a NEW chat: the window appears with the first message already in it
    panes[20] = [f"{_stamp(7200)}|older line", f"{_stamp()}|!np"]
    wins.append(SimpleNamespace(handle=20, pid=2, title="zdevz (IM)"))
    got = a._im_lines()
    assert [(m.user, m.text, m.is_im) for m in got] == [("zdevz", "!np", True)]
    panes[20] = [*panes[20], f"{_stamp()}|second"]
    assert [m.text for m in a._im_lines()] == ["second"]


def test_windows_without_im_pane_are_not_rescanned(monkeypatch):
    panes: dict[int, list[str] | None] = {30: None}  # e.g. the buddy list window
    wins = [SimpleNamespace(handle=30, pid=2, title="Camfrog Video Chat")]
    a, reads = _adapter(monkeypatch, panes, wins)
    a._im_lines()
    a._im_lines()
    assert reads == [30]


def test_im_message_reaches_the_viewer_snapshot():
    cfg = Config()
    cfg.im_auto_reply_enabled = True
    cfg.im_auto_reply_message = "bot here"
    e = Engine(cfg, NullAdapter())
    e.exec.submit = lambda *a, **k: None  # type: ignore[method-assign]  # router not needed here
    done = threading.Event()

    def run():
        e._handle_im(ChatMessage("zdevz", "hello", is_im=True))
        done.set()

    threading.Thread(target=run, daemon=True).start()
    assert done.wait(3), "IM handling deadlocked"
    seq, _ver, entries = e.im_snapshot()
    assert seq == 1 and entries == [("zdevz", "hello")]

