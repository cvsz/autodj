"""The bot must not read or type while Camfrog shows another page.

Live 2026-11-22 07:07: Camfrog's window switched to its room list (same window,
title 'รายชื่อห้องสนทนา').  The adapter kept its cached chat panes, so for five
hours every send clicked and pasted into the room list at the old message-box
position, and the reader kept re-reading the cached history.
"""

from __future__ import annotations

import logging
import threading

import pytest

from autodj import webchat
from autodj.adapters import uia
from autodj.config import Config

ROOM_TITLE = "ZeaZDev, หัวข้อ: ZeaZDev"
LIST_TITLE = "รายชื่อห้องสนทนา"


@pytest.fixture
def env(monkeypatch):
    state = {"title": ROOM_TITLE, "panes": ("VIEW2", "INPUT2"), "lookups": 0}

    def find(win, view_title, input_title):
        state["lookups"] += 1
        return state["panes"]

    monkeypatch.setattr(uia, "_window_title", lambda h: state["title"])
    monkeypatch.setattr(webchat, "find_web_panes", find)
    a = uia.UiaAdapter.__new__(uia.UiaAdapter)
    a.cfg = Config()
    a.handle = 1001
    a.win = object()
    a.com_lock = threading.RLock()
    a._web, a._view, a._input = True, "VIEW", "INPUT"
    a._web_room = True
    a._room_title = ROOM_TITLE
    a._room_hidden = False
    a._hidden_title = None
    a._hidden_checked = 0.0
    return a, state


def test_same_title_is_one_cheap_check(env):
    a, state = env
    a._check_room_shown()
    assert state["lookups"] == 0 and a._view == "VIEW"


def test_room_list_shown_raises_and_drops_stale_panes(env, caplog):
    a, state = env
    state["title"], state["panes"] = LIST_TITLE, (None, None)
    with caplog.at_level(logging.WARNING, logger="autodj"):
        with pytest.raises(uia.RoomHiddenError):
            a._check_room_shown()
        with pytest.raises(uia.RoomHiddenError):
            a._check_room_shown()  # within 5 s: no new lookup, no second warning
    assert a._view is None and a._input is None
    assert state["lookups"] == 1
    assert sum("instead of the room chat" in r.getMessage() for r in caplog.records) == 1


def test_topic_change_finds_the_panes_again(env):
    a, state = env
    state["title"] = "ZeaZDev, หัวข้อ: new topic"
    a._check_room_shown()
    assert (a._view, a._input, a._room_title) == ("VIEW2", "INPUT2", state["title"])


def test_room_shown_again_resumes(env, caplog):
    a, state = env
    state["title"], state["panes"] = LIST_TITLE, (None, None)
    with pytest.raises(uia.RoomHiddenError):
        a._check_room_shown()
    state["title"], state["panes"] = ROOM_TITLE, ("VIEW3", "INPUT3")
    with caplog.at_level(logging.INFO, logger="autodj"):
        a._check_room_shown()
    assert a._view == "VIEW3" and a._room_hidden is False
    assert any("shown again" in r.getMessage() for r in caplog.records)


def test_send_types_nothing_while_the_room_is_hidden(env):
    a, state = env
    state["title"], state["panes"] = LIST_TITLE, (None, None)

    def boom(*args, **kwargs):
        raise AssertionError("must not type")

    a._send_fg = boom
    a._attempt_background_send = boom
    with pytest.raises(uia.RoomHiddenError):
        a._do_send("now playing")


def test_reader_keeps_baseline_and_reads_ims_while_hidden(env, monkeypatch):
    a, _ = env
    reads = iter([["Ann: x"], uia.RoomHiddenError("list"), ["Ann: x", "Bob: hi"]])

    def lines():
        r = next(reads)
        if isinstance(r, Exception):
            raise r
        return r

    im_polls = []
    a._lines = lines
    a._im_lines = lambda: im_polls.append(1) or []
    a.rx = __import__("re").compile(a.cfg.line_regex)
    a.join_rx = None
    monkeypatch.setattr(uia.time, "sleep", lambda s: None)
    gen = a.messages()
    first = next(gen)
    assert first.user == "Ann" and first.event == "seen"
    msg = next(gen)  # the hidden poll yields nothing; the next one sees Bob
    assert (msg.user, msg.text) == ("Bob", "hi")
    assert len(im_polls) >= 2  # IMs were still read during the hidden poll
