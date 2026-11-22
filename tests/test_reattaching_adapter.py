"""ReattachingAdapter: a bot started before the Camfrog room window was open
attaches by itself once the window appears (it used to stay on NullAdapter
until restarted, so IMs were never read or answered)."""

from __future__ import annotations

import threading
import types

from autodj.adapters import ReattachingAdapter
from autodj.adapters.base import ChatAdapter, ChatMessage
from autodj.config import Config


class _Inner(ChatAdapter):
    def __init__(self, msgs=()):
        self.msgs = list(msgs)
        self.sent: list[str] = []
        self.ims: list[tuple[str, str]] = []
        self.closed = False

    def messages(self):
        yield from self.msgs

    def send(self, text):
        self.sent.append(text)

    def send_im(self, user, text):
        self.ims.append((user, text))

    def close(self):
        self.closed = True


def _builder(fail_times: int, inner: _Inner):
    calls = {"n": 0}

    def build(cfg):
        calls["n"] += 1
        if calls["n"] <= fail_times:
            raise RuntimeError("no visible window matches 'ZeaZDev'")
        return inner

    return build, calls


def test_send_drops_until_attached_then_delivers():
    inner = _Inner()
    build, calls = _builder(1, inner)
    ad = ReattachingAdapter(Config(), build=build, interval=0.0)
    ad.send("first")  # room closed: dropped, not raised
    assert inner.sent == [] and ad.delivers is False
    ad.send("second")  # room open now
    assert inner.sent == ["second"] and ad.delivers is True
    assert calls["n"] == 2


def test_retry_waits_for_interval():
    inner = _Inner()
    build, calls = _builder(1, inner)
    ad = ReattachingAdapter(Config(), build=build, interval=3600.0)
    ad.send("a")
    ad.send("b")  # still inside the retry interval: no second build attempt
    assert calls["n"] == 1 and inner.sent == []


def test_messages_waits_then_yields_from_real_adapter():
    msg = ChatMessage("zdevz", "!play song", is_im=True)
    inner = _Inner([msg])
    build, _ = _builder(2, inner)
    ad = ReattachingAdapter(Config(), build=build, interval=0.0)
    ad._closed.wait = types.MethodType(lambda self, t: False, ad._closed)  # no real sleeping
    assert list(ad.messages()) == [msg]


def test_send_im_delegates_once_attached():
    inner = _Inner()
    build, _ = _builder(1, inner)
    ad = ReattachingAdapter(Config(), build=build, interval=0.0)
    assert ad.send_im is None
    fn = ad.send_im
    assert fn is not None
    fn("zdevz", "hi")
    assert inner.ims == [("zdevz", "hi")]


def test_close_stops_waiting_messages_loop():
    build, _ = _builder(10**6, _Inner())
    ad = ReattachingAdapter(Config(), build=build, interval=0.0)
    out: list = []
    t = threading.Thread(target=lambda: out.extend(ad.messages()))
    t.start()
    ad.close()
    t.join(timeout=5)
    assert not t.is_alive() and out == []


def test_close_closes_attached_adapter():
    inner = _Inner()
    build, _ = _builder(0, inner)
    ad = ReattachingAdapter(Config(), build=build, interval=0.0)
    ad.send("x")
    ad.close()
    assert inner.closed is True


def test_gui_startup_without_room_uses_reattaching_adapter(monkeypatch):
    from autodj import __main__ as main_mod

    def boom(cfg):
        raise RuntimeError("no visible window matches 'ZeaZDev'")

    monkeypatch.setattr(main_mod, "build_adapter", boom)
    ad = main_mod._build_adapter(types.SimpleNamespace(gui=True), Config())
    assert isinstance(ad, ReattachingAdapter)
