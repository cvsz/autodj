"""Regression tests for the audit findings fixed in 0.3.18."""

from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from types import SimpleNamespace

from test_core import FakeAdapter, FakePlayer

from autodj import engine as engine_mod
from autodj.adapters import Composite, ReattachingAdapter, uia
from autodj.config import Config
from autodj.engine import Engine
from autodj.library import MetadataCache


def _engine(**kw):
    return Engine(Config(lang="th", **kw), FakeAdapter(), player=FakePlayer(), index=None)


# 5. IM replies from the chat reader thread do not block it
def test_send_im_on_the_reader_thread_is_handed_off():
    release = threading.Event()
    sent: list[tuple[str, str]] = []

    class SlowIm(FakeAdapter):
        def send_im(self, user, text):
            release.wait(5)  # Camfrog: waits for the user, the window, the echo
            sent.append((user, text))

    e = Engine(Config(lang="th"), SlowIm(), player=FakePlayer(), index=None)
    e._chat_thread_ident = threading.get_ident()  # we are "the reader"
    t0 = time.monotonic()
    assert e.send_im("amy", "สวัสดี") is True
    assert time.monotonic() - t0 < 0.5  # returned at once
    assert sent == []
    release.set()
    e._im_exec.shutdown(wait=True)
    assert sent == [("amy", "สวัสดี")]
    assert e.im_log[-1][1] == "สวัสดี"


def test_send_im_elsewhere_stays_synchronous():
    sent: list[tuple[str, str]] = []

    class Im(FakeAdapter):
        def send_im(self, user, text):
            sent.append((user, text))

    e = Engine(Config(lang="th"), Im(), player=FakePlayer(), index=None)
    assert e.send_im("amy", "hi") is True
    assert sent == [("amy", "hi")]


# 15. background sends are tried again after the pause, counted once per failure
def test_background_send_comes_back_after_the_pause(monkeypatch):
    a = uia.UiaAdapter.__new__(uia.UiaAdapter)
    a._bg_fails_lock = threading.Lock()
    a._bg_fails = 0
    a.cfg = SimpleNamespace(send_verify=True)
    assert a._bg_after_loop("x", False, None, "auto") == "fallback"
    assert a._bg_fails == 1  # one failure counts once
    a._bg_after_loop("x", False, None, "auto")
    assert a._bg_allowed("auto") is False
    a._bg_retry_at = time.monotonic() - 1  # pause over
    assert a._bg_allowed("auto") is True and a._bg_fails == 0


# 16. a hot-reloaded config reaches the running chat adapter
def test_reloaded_config_reaches_the_adapter():
    a = uia.UiaAdapter.__new__(uia.UiaAdapter)
    a.com_lock = threading.RLock()
    a.cfg = Config()
    a.rx = re.compile(a.cfg.line_regex)
    a._view = a._input = object()
    new = Config(line_regex=r"^(?P<user>\S+) says (?P<text>.+)$", poll_interval=1.5)
    c = Composite(a, a)
    r = ReattachingAdapter(Config(), build=lambda cfg: c)
    r._inner = c
    r.apply_config(new)
    assert a.cfg is new and r.cfg is new
    assert a.rx.pattern == new.line_regex
    assert a._view is None and a._input is None  # panes looked up again


def test_engine_reload_calls_apply_config():
    got = []

    class A(FakeAdapter):
        def apply_config(self, cfg):
            got.append(cfg)

    e = Engine(Config(lang="th"), A(), player=FakePlayer(), index=None)
    new = Config(lang="th", poll_interval=2.0)
    e._on_config_reload(new)
    assert got == [new]


# 17. room presence expires; the voteskip count only uses recently seen nicks
def test_room_presence_expires(monkeypatch):
    e = _engine()
    clock = [1000.0]
    monkeypatch.setattr(engine_mod.time, "monotonic", lambda: clock[0])
    e._update_participant_count("amy")
    clock[0] += engine_mod.ACTIVE_WINDOW_S + 1
    e._update_participant_count("bob")
    assert e.participant_count == 1  # amy no longer active
    assert "amy" in e._active_room_users  # but still present
    clock[0] += engine_mod.ROOM_PRESENCE_TTL_S
    e._update_participant_count("bob")
    assert "amy" not in e._active_room_users
    assert e._active_room_users == {"bob"}


# 19. playback failures/successes reach the health report
def test_playback_failures_are_reported_by_health_check():
    e = _engine()
    for _ in range(engine_mod._CIRCUIT_BREAKER_FAILURE_THRESHOLD):
        e._record_circuit_failure()
    assert e.health_check()["checks"]["circuit_breaker"]["ok"] is False
    e._record_circuit_success()
    assert e.health_check()["checks"]["circuit_breaker"]["ok"] is True


def test_track_failed_records_a_playback_failure():
    from autodj.models import Track

    e = _engine()
    e._track_failed(Track("https://youtu.be/x", "x", 60, "amy"), 1)
    assert e._circuit_breaker_failures == 1


# 20. the metadata cache saves a snapshot and lives in the cache folder
def test_metadata_cache_save_is_safe_while_entries_are_added(tmp_path):
    cache = MetadataCache([str(tmp_path / "music")], cache_dir=tmp_path / "cache")
    stop = threading.Event()

    def writer():
        i = 0
        while not stop.is_set():
            cache.set(Path(f"/m/{i}.mp3"), 1.0, f"t{i}", None, 1.0)
            i += 1

    t = threading.Thread(target=writer, daemon=True)
    t.start()
    try:
        for _ in range(50):
            cache.save()  # used to raise "dictionary changed size during iteration"
    finally:
        stop.set()
        t.join(2)
    cache.save()
    data = json.loads((tmp_path / "cache" / "autodj_metadata_cache.json").read_text("utf-8"))
    assert data["entries"]
    assert not (tmp_path / "music").exists()  # nothing written into the music folder
