"""Test that _pop_next_track prioritizes user requests over autoplay pool."""

from autodj.adapters import NullAdapter
from autodj.config import Config
from autodj.engine import Engine
from autodj.models import Track


def test_pop_next_track_requests_take_priority():
    """_pop_next_track returns a user request when requests exist, even if pool has tracks."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)

    req_track = Track(source="req1", title="Request", duration=180.0, requester="user")
    pool_track = Track(source="pool1", title="Pool", duration=180.0, requester="AutoDJ")

    eng.queue.add_request(req_track)
    eng.queue.add_pool([pool_track])

    t = eng._pop_next_track()
    assert t is not None, "Should have popped a track"
    assert t.source == "req1", f"Expected req1 (user request priority), got {t.source}"


def test_pop_next_track_no_requests_returns_pool():
    """When no user requests, _pop_next_track falls back to the autoplay pool."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)

    pool_track = Track(source="pool1", title="Pool", duration=180.0, requester="AutoDJ")
    eng.queue.add_pool([pool_track])

    t = eng._pop_next_track()
    assert t is not None, "Should have popped a pool track when no requests"
    assert t.source == "pool1", f"Expected pool1, got {t.source}"


def test_pop_next_track_no_tracks_returns_none():
    """When no requests and no pool, _pop_next_track returns None."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)

    t = eng._pop_next_track()
    assert t is None, "Should return None when no tracks at all"


def test_pop_next_track_exhausts_requests_then_pool():
    """After all user requests are popped, fall back to autoplay pool."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)

    req_track = Track(source="req1", title="Request", duration=180.0, requester="user")
    pool_track = Track(source="pool1", title="Pool", duration=180.0, requester="AutoDJ")

    eng.queue.add_request(req_track)
    eng.queue.add_pool([pool_track])

    # First pop: user request
    t = eng._pop_next_track()
    assert t.source == "req1"

    # Second pop: no more requests, fall back to pool
    t = eng._pop_next_track()
    assert t is not None, "Should fall back to pool after requests exhausted"
    assert t.source == "pool1", f"Expected pool1, got {t.source}"

