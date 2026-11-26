"""Auto ads are held while the Camfrog room chat is not open.

Live 2026-11-27: "auto-reply sent" was logged while the room window was closed and
the adapter dropped every one of those ads ("Message dropped").
"""

from __future__ import annotations

import json

from test_core import FakeAdapter, FakePlayer, out

from autodj.adapters import Composite, ReattachingAdapter
from autodj.config import Config
from autodj.engine import Engine


class _Ticks:
    """stop_evt stand-in: runs the loop *n* times, then stops it."""

    def __init__(self, n: int, on_tick=None):
        self.n, self.on_tick, self.calls = n, on_tick, 0

    def wait(self, _timeout=None) -> bool:
        self.calls += 1
        if self.on_tick:
            self.on_tick(self.calls)
        return self.calls > self.n

    def is_set(self) -> bool:
        return self.calls > self.n


class _RoomAdapter(FakeAdapter):
    ready = False

    @property
    def room_ready(self) -> bool:
        return self.ready


def _engine(tmp_path, adapter):
    ads = tmp_path / "ads-list.json"
    ads.write_text(json.dumps({"messages": ["only ad"]}), "utf-8")
    cfg = Config(auto_reply_enabled=True, auto_reply_interval=60.0, auto_reply_file=str(ads))
    return Engine(cfg, adapter, player=FakePlayer(), index=None)


def test_ads_are_held_while_the_room_is_not_open(tmp_path):
    a = _RoomAdapter()
    e = _engine(tmp_path, a)
    e.stop_evt = _Ticks(3)
    e._auto_reply_loop()
    assert out(e) == []


def test_ads_resume_when_the_room_opens(tmp_path):
    a = _RoomAdapter()
    e = _engine(tmp_path, a)

    def open_room(call):
        a.ready = call >= 3

    e.stop_evt = _Ticks(3, open_room)
    e._auto_reply_loop()
    assert out(e) == ["only ad"]  # slots 1-2 held, slot 3 sent


def test_adapters_without_the_property_still_send(tmp_path):
    e = _engine(tmp_path, FakeAdapter())
    e.stop_evt = _Ticks(1)
    e._auto_reply_loop()
    assert out(e) == ["only ad"]


def test_reattaching_adapter_is_not_ready_before_attaching():
    def fail(_cfg):
        raise RuntimeError("room window closed")

    r = ReattachingAdapter(Config(), build=fail)
    assert r.room_ready is False
    r._inner = _RoomAdapter()
    assert r.room_ready is False
    r._inner.ready = True
    assert r.room_ready is True


def test_composite_asks_the_sender():
    sender = _RoomAdapter()
    c = Composite(FakeAdapter(), sender)
    assert c.room_ready is False
    sender.ready = True
    assert c.room_ready is True
