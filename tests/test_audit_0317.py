"""Regression tests for the 0.3.17 deep-audit findings (read-only audit, then fixed)."""

from __future__ import annotations

import threading
import time
import tomllib
from types import SimpleNamespace

from test_core import FakeAdapter, FakePlayer, out

from autodj.adapters import uia
from autodj.adapters.base import ChatMessage
from autodj.commands import Router
from autodj.config import Config
from autodj.engine import Engine
from autodj.gui import _toml_list
from autodj.models import Track
from autodj.playqueue import PlayQueue


def _engine(**kw):
    cfg = Config(lang="th", **kw)
    return Engine(cfg, FakeAdapter(), player=FakePlayer(), index=None)


# 1. our IM reply read back must not mark the other user as our own account
def test_im_echo_does_not_mark_the_sender_as_own_account():
    e = _engine(welcome_message_enabled=True, welcome_message_cooldown=0)
    e._remember_sent("ขอเพลงผ่าน IM ได้เลยครับ")
    assert e._should_ignore_message(ChatMessage("amy", "ขอเพลงผ่าน IM ได้เลยครับ", is_im=True))
    assert not e._is_own_account("amy")
    assert e._greet_user("amy") is True


def test_room_echo_still_teaches_the_own_account():
    e = _engine()
    e._remember_sent("now playing x")
    assert e._should_ignore_message(ChatMessage("Seaza", "now playing x"))
    assert e._is_own_account("Seaza")


# 6. the first IM of a window whose first read was empty is delivered
def test_first_im_after_an_empty_first_read_is_delivered(monkeypatch):
    a = uia.UiaAdapter.__new__(uia.UiaAdapter)
    a.com_lock = threading.RLock()
    a._im_prev = {300: []}  # read before: pane found but still empty
    a._im_not_im = {}
    stamp = time.strftime("%H:%M")
    monkeypatch.setattr(a, "_read_im_window", lambda w: ([f"{stamp}|!play x"], "Bob"))
    got = a._im_window_messages(SimpleNamespace(handle=300, title="Bob"), first_scan=False)
    assert [(m.user, m.text) for m in got] == [("Bob", "!play x")]


# 18. closed IM windows are forgotten by send_im's handle map
def test_closed_im_window_handle_is_forgotten(monkeypatch):
    import autodj.windows as windows

    a = uia.UiaAdapter.__new__(uia.UiaAdapter)
    a.cfg = SimpleNamespace(process_re="")
    a.handle = 1
    a.com_lock = threading.RLock()
    a._im_prev, a._im_not_im = {}, {}
    a._im_handles = {"bob": 300, "amy": 400}
    monkeypatch.setattr(
        windows, "candidates", lambda *x, **k: [SimpleNamespace(handle=400, pid=2, title="Amy")]
    )
    monkeypatch.setattr(a, "_read_im_window", lambda w: ([], "Amy"))
    a._im_lines()
    assert a._im_handles == {"amy": 400}


# 7. an IM that is not a command does not spend the command cooldown
def test_plain_im_does_not_spend_the_cooldown():
    e = _engine(cooldown=3.0, im_require_room_presence=False)
    r = Router(e)
    r.handle(ChatMessage("amy", "hi there", is_im=True))  # no such command, no plugin
    assert "amy" not in r.last
    r.handle(ChatMessage("amy", "!np", is_im=True))
    assert "amy" in r.last  # the built-in ran and spent it


# 8. health_check returns (it deadlocked on the circuit breaker lock)
def test_health_check_returns():
    e = _engine()
    result: dict = {}
    t = threading.Thread(target=lambda: result.update(e.health_check()), daemon=True)
    t.start()
    t.join(5)
    assert not t.is_alive(), "health_check deadlocked"
    assert "checks" in result or result  # a report came back


# 22. a delayed welcome re-checks the never-greet rule
def test_delayed_welcome_rechecks_never_greet():
    e = _engine()
    e.blocked.add("amy")  # blocked while the welcome waited
    e._send_welcome_after_delay("welcome amy", "amy")
    assert out(e) == []
    e._send_welcome_after_delay("welcome bob", "bob")
    assert out(e) == ["welcome bob"]


# 10. settings lists are written as TOML that round-trips (repr doubled backslashes)
def test_settings_lists_round_trip_backslashes_and_quotes():
    values = [r"D:\Music\ไทย", 'it\'s "quoted"', ""]
    text = f"music_dirs = {_toml_list(values)}\n"
    assert tomllib.loads(text)["music_dirs"] == values
    again = f"music_dirs = {_toml_list(tomllib.loads(text)['music_dirs'])}\n"
    assert again == text  # saving twice changes nothing


# 12. different Thai titles are not duplicates; case/punctuation still fold
def test_thai_titles_with_different_marks_are_different_songs():
    key = PlayQueue._dedupe_key
    assert key(Track("a", "ปิ่น")) != key(Track("b", "ปั่น"))
    assert key(Track("a", "เพลงรัก")) != key(Track("b", "เพลงริก"))
    assert key(Track("a", "Love Song!")) == key(Track("b", "love   song"))
    assert key(Track("a", "รักเอย (Official)")) == key(Track("b", "รักเอย - official"))
