"""Regression tests for the deep-audit logic fixes (see CHANGELOG "Unreleased")."""

from __future__ import annotations

import asyncio
import os
import threading
from types import SimpleNamespace

import pytest

from autodj import commands
from autodj.adapters import NullAdapter
from autodj.config import Config
from autodj.engine import Engine
from autodj.models import Track
from autodj.player import _MISSING, MpvPlayer, _ipc_reply
from autodj.playqueue import PlayQueue
from autodj.updater import Updater


def _engine(tmp_path=None) -> Engine:
    cfg = Config()
    eng = Engine(cfg, NullAdapter(), cfg_path=str(tmp_path / "config.toml") if tmp_path else None)
    eng.say = lambda *_a, **_k: True  # type: ignore[method-assign]
    return eng


# ---- PlayQueue ---------------------------------------------------------------


def test_add_request_returns_zero_for_dropped_duplicate():
    q = PlayQueue()
    assert q.add_request(Track("a1", "Song A", 100, "bob")) == 1
    dup = Track("a2", "Song A", 100, "bob")  # same title, other video id
    assert q.add_request(dup) == 0
    assert len(q.requests) == 1
    assert dup.is_request is False  # a dropped track is not mutated


def test_add_request_dedupe_false_forces_insert_and_reports_position():
    q = PlayQueue()
    q.add_request(Track("a1", "Song A", 100, "bob"))
    q.add_request(Track("b1", "Song B", 100, "bob"))
    again = Track("a1", "Song A", 100, "bob")
    assert q.add_request(again, position=0, dedupe=False) == 1
    assert q.requests[0] is again


def test_replace_request_bumps_version():
    q = PlayQueue()
    old = Track("ytsearch1:x", "x", None, "bob")
    q.add_request(old)
    v = q.version
    new = Track("https://y/1", "X Resolved", 120, "bob")
    assert q.replace_request(old, new) is True
    assert q.requests[0] is new and q.version != v
    assert q.replace_request(old, new) is False


# ---- Engine: failed requests must not stall playback ----------------------------


def test_only_failed_requests_fall_through_to_pool():
    eng = _engine()
    dead = Track("dead", "Dead Link", 100, "bob")
    eng.queue.add_request(dead)
    eng.queue.add_pool([Track("pool1", "Pool", 100)])
    eng._track_failed(Track("dead", "Dead Link", 100, "bob"), 1)
    t = eng._pop_next_track()
    assert t is not None and t.source == "pool1"  # used to return None forever
    assert list(eng.queue.requests) == [dead]  # failed request kept, FIFO place intact
    assert eng._has_playable_request() is False


def test_failed_request_becomes_playable_after_ttl(monkeypatch):
    eng = _engine()
    eng.queue.add_request(Track("dead", "Dead Link", 100, "bob"))
    eng._track_failed(Track("dead", "Dead Link", 100, "bob"), 1)
    key = eng._track_key(Track("dead", "Dead Link", 100, "bob"))
    eng._recent_failed[key] = 0.0  # expired
    assert eng._has_playable_request() is True
    assert eng._pop_next_track().source == "dead"


def test_skipped_failed_requests_keep_front_order():
    eng = _engine()
    f1, f2, ok = (
        Track("f1", "Fail One", 1, "a"),
        Track("f2", "Fail Two", 1, "b"),
        Track("ok", "Fine", 1, "c"),
    )
    for t in (f1, f2, ok):
        eng.queue.add_request(t)
    eng._track_failed(Track("f1", "Fail One", 1, "a"), 1)
    eng._track_failed(Track("f2", "Fail Two", 1, "b"), 2)
    assert eng._pop_next_track() is ok
    assert list(eng.queue.requests) == [f1, f2]


def test_pool_track_not_refused_by_failed_request():
    """_play_one_track must start a pool song when only failed requests wait."""
    eng = _engine()
    eng.queue.add_request(Track("dead", "Dead Link", 100, "bob"))
    eng._track_failed(Track("dead", "Dead Link", 100, "bob"), 1)
    played = []
    eng.player = SimpleNamespace(  # type: ignore[assignment]
        play=lambda src, vol, dur: played.append(src) or True, skipped=False, stop=lambda: None
    )
    eng._play_one_track(Track("pool1", "Pool", 100), 0)
    assert played == ["pool1"]


def test_prev_requeues_even_when_title_already_queued():
    eng = _engine()
    stopped = []
    eng.player = SimpleNamespace(stop=lambda: stopped.append(1))  # type: ignore[assignment]
    last = Track("s1", "Same", 100, "AutoDJ")
    eng.history.appendleft(last)
    eng.queue.add_request(Track("s2", "Same", 100, "bob"))
    eng.prev()
    assert eng.queue.requests[0] is last
    assert stopped == [1]


def test_record_request_is_thread_safe(tmp_path):
    eng = _engine(tmp_path)
    threads = [
        threading.Thread(target=eng.record_request, args=(f"s{i}", f"T{i}")) for i in range(20)
    ]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    import json

    data = json.loads((tmp_path / "top_requests.json").read_text(encoding="utf-8"))
    assert len(data["requests"]) == 20  # no lost updates


# ---- commands: duplicate requests are reported, not "queued" -------------------


def test_play_duplicate_title_raises_already_queued(monkeypatch):
    eng = _engine()
    eng.queue.add_request(Track("v1", "Hit Song", 100, "bob"))
    monkeypatch.setattr(eng, "resolve", lambda *_a: [Track("v2", "Hit Song", 100, "bob")])
    recorded = []
    monkeypatch.setattr(eng, "record_request", lambda *a: recorded.append(a))
    msg = SimpleNamespace(user="bob", text="!play hit", local=False, is_im=False)
    with pytest.raises(commands.UserError):
        commands._play(eng, msg, "hit song", True)
    assert recorded == []  # no stats for a song that was never queued
    assert len(eng.queue.requests) == 1


# ---- mpv IPC reply parsing -------------------------------------------------------


def test_ipc_reply_skips_event_lines():
    buf = b'{"event":"property-change","id":1}\n{"data":42.5,"error":"success","request_id":7}\n'
    assert _ipc_reply(buf, 7) == 42.5
    assert _ipc_reply(buf, 8) is _MISSING
    assert _ipc_reply(b'{"error":"property unavailable","request_id":3}\n', 3) is None
    assert _ipc_reply(b'{"data":1,"request_', 1) is _MISSING  # partial line


def test_cmd_get_handles_event_before_reply(monkeypatch):
    p = MpvPlayer(SimpleNamespace(mpv_path="mpv", audio_device=""))
    p._ipc = "pipe"

    def fake_read(_ipc, data, _timeout, request_id):
        return b'{"event":"seek"}\n{"data":12.0,"error":"success","request_id":%d}\n' % request_id

    monkeypatch.setattr(p, "_ipc_read_windows", fake_read)
    monkeypatch.setattr(p, "_ipc_read_unix", fake_read)
    assert p._cmd_get("get_property", "time-pos") == 12.0


# ---- library: junctions are not followed ----------------------------------------


def test_is_link_detects_junction_like_entries():
    from autodj.library import _is_link

    class E:
        def __init__(self, sym, junc):
            self._s, self._j = sym, junc

        def is_symlink(self):
            return self._s

        def is_junction(self):
            return self._j

    assert _is_link(E(True, False)) and _is_link(E(False, True))
    assert not _is_link(E(False, False))
    assert not _is_link(SimpleNamespace(is_symlink=lambda: False))  # Python 3.11 DirEntry


# ---- updater batch script --------------------------------------------------------


def test_update_script_quotes_and_escapes_paths(tmp_path):
    exe = tmp_path / "Program Files (x86)" / "50%off" / "AutoDJ.exe"
    exe.parent.mkdir(parents=True)
    Updater(Config())._write_update_script(exe, exe.with_name("AutoDJ.next.exe"), "v1&calc")
    text = (exe.parent / "autodj_update.bat").read_text(encoding="utf-8")
    assert "chcp 65001" in text
    assert "50%%off" in text and "50%off" not in text.replace("50%%off", "")
    assert '(echo ERROR: "' in text  # ")" in a path can no longer close the block
    assert "v1calc" in text and "&calc" not in text


# ---- webhook hardening -------------------------------------------------------------

fastapi = pytest.importorskip("fastapi")


def test_raw_body_middleware_stops_on_disconnect_and_caps_size():
    from autodj.webhook.auth import MAX_BODY_BYTES, RawBodyMiddleware

    async def app(scope, receive, send):  # pragma: no cover - must not be reached
        raise AssertionError("downstream app reached")

    async def run(messages):
        mw = RawBodyMiddleware(app)
        sent = []
        it = iter(messages)
        polls = 0

        async def receive():
            nonlocal polls
            polls += 1
            if polls > 50:
                raise AssertionError("busy loop after disconnect")
            return next(it, {"type": "http.disconnect"})

        async def send(msg):
            sent.append(msg)

        scope = {"type": "http", "method": "POST", "path": "/x", "headers": [], "query_string": b""}
        await mw(scope, receive, send)
        return next(m["status"] for m in sent if m["type"] == "http.response.start")

    assert asyncio.run(run([{"type": "http.disconnect"}])) == 400
    big = [{"type": "http.request", "body": b"x" * (MAX_BODY_BYTES + 1), "more_body": False}]
    assert asyncio.run(run(big)) == 413


def _signed_post(client, path: str, payload: dict, secret: str = "test-secret-key-12345"):  # noqa: S107
    import hashlib
    import hmac
    import json
    import time

    body = json.dumps(payload).encode()
    ts = str(int(time.time()))
    sig = hmac.new(secret.encode(), f"{ts}.POST.{path}.".encode() + body, hashlib.sha256)
    return client.post(
        path,
        content=body,
        headers={
            "X-Timestamp": ts,
            "X-Signature": sig.hexdigest(),
            "Content-Type": "application/json",
        },
    )


def test_request_body_endpoints_accept_valid_calls():
    """/say, /shuffle and /repeat used to answer every call with 422."""
    from fastapi.testclient import TestClient

    from autodj.webhook.models import WebhookConfig
    from autodj.webhook.server import create_webhook_app

    said: list[str] = []
    shuffles: list[bool] = []
    queue = SimpleNamespace(set_shuffle=shuffles.append, repeat="off")
    engine = SimpleNamespace(say=said.append, queue=queue)
    cfg = WebhookConfig(enabled=True, secret="test-secret-key-12345")  # noqa: S106
    client = TestClient(create_webhook_app(cfg, engine))
    assert _signed_post(client, "/webhook/say", {"text": "hello"}).status_code == 200
    assert _signed_post(client, "/webhook/shuffle", {"enabled": False}).status_code == 200
    assert _signed_post(client, "/webhook/repeat", {"mode": "one"}).status_code == 200
    assert said == ["hello"] and shuffles == [False] and queue.repeat == "one"


def test_say_endpoint_rejects_huge_text():
    import hashlib
    import hmac
    import json
    import time

    from fastapi.testclient import TestClient

    from autodj.webhook.models import WebhookConfig
    from autodj.webhook.server import MAX_SAY_CHARS, create_webhook_app

    secret = "test-secret-key-12345"  # noqa: S105
    said = []
    engine = SimpleNamespace(say=said.append)
    client = TestClient(create_webhook_app(WebhookConfig(enabled=True, secret=secret), engine))
    body = json.dumps({"text": "x" * (MAX_SAY_CHARS + 1)}).encode()
    ts = str(int(time.time()))
    sig = hmac.new(
        secret.encode(), f"{ts}.POST./webhook/say.".encode() + body, hashlib.sha256
    ).hexdigest()
    r = client.post(
        "/webhook/say",
        content=body,
        headers={"X-Timestamp": ts, "X-Signature": sig, "Content-Type": "application/json"},
    )
    assert r.status_code == 413 and said == []


def test_uia_im_scan_skips_own_and_room_windows(monkeypatch):
    from autodj.adapters import uia

    a = uia.UiaAdapter.__new__(uia.UiaAdapter)
    a.cfg = SimpleNamespace(process_re="")
    a.handle = 100
    a.com_lock = threading.RLock()
    read = []
    wins = [
        SimpleNamespace(handle=100, pid=1, title="room"),
        SimpleNamespace(handle=200, pid=os.getpid(), title="mine"),
        SimpleNamespace(handle=300, pid=2, title="Bob (IM)"),
    ]
    import autodj.windows as w

    monkeypatch.setattr(w, "candidates", lambda *a, **k: wins)
    monkeypatch.setattr(a, "_read_im_window", lambda win: read.append(win.handle) or ([], "Bob"))
    a._im_prev = {999: ["old"]}
    a._im_lines()
    assert read == [300]
    assert 999 not in a._im_prev  # closed window baseline dropped


# ---- IM marker parsing must not rewrite nicknames ----------------------------


def test_parse_line_im_marker_needs_separate_word():
    import re

    from autodj.adapters.base import parse_line

    rx = re.compile(r"(?P<user>[^:]+?):\s*(?P<text>.*)")
    m = parse_line("[IM] Bob: !np", rx)
    assert m is not None and m.user == "Bob" and m.is_im
    m = parse_line("PM Bob: hi", rx)
    assert m is not None and m.user == "Bob" and m.is_im
    spoof = parse_line("[IM]Admin: !skip", rx)  # a nickname, not a marker
    assert spoof is not None and spoof.user == "[IM]Admin" and not spoof.is_im
    plain = parse_line("IMogen: hello", rx)
    assert plain is not None and plain.user == "IMogen" and not plain.is_im
