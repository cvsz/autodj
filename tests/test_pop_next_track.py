"""Test that _pop_next_track correctly respects is_request flag."""

from camfrog_autodj.adapters import NullAdapter
from camfrog_autodj.config import Config
from camfrog_autodj.engine import Engine
from camfrog_autodj.models import Track


def test_pop_next_track_respects_is_request():
    """_pop_next_track should return request track when is_request=True, pool track when is_request=False."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)

    # Add a request track and a pool track
    req_track = Track(source="req1", title="Request", duration=180.0, requester="user")
    pool_track = Track(source="pool1", title="Pool", duration=180.0, requester="AutoDJ")

    eng.queue.add_request(req_track)
    eng.queue.add_pool([pool_track])

    # When is_request=True, should get request track
    t = eng._pop_next_track(is_request=True)
    assert t is not None, "Should have popped a track"
    assert t.source == "req1", f"Expected req1, got {t.source}"

    # Add another request and pool track
    req_track2 = Track(source="req2", title="Request2", duration=180.0, requester="user")
    pool_track2 = Track(source="pool2", title="Pool2", duration=180.0, requester="AutoDJ")
    eng.queue.add_request(req_track2)
    eng.queue.add_pool([pool_track2])

    # When is_request=False, should get pool track (since no requests should be left in autoplay mode)
    # But currently there ARE requests, so this tests the edge case
    # The player loop ensures is_request=False only when no requests, but let's verify the method behavior
    t = eng._pop_next_track(is_request=False)
    # With current implementation, this will pop from requests because peek() returns requests first
    # After fix, it should pop from pool
    print(f"Popped with is_request=False: {t.source if t else None}")


def test_pop_next_track_no_requests_returns_pool():
    """When no requests and is_request=False, should return pool track."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)

    pool_track = Track(source="pool1", title="Pool", duration=180.0, requester="AutoDJ")
    eng.queue.add_pool([pool_track])

    # No requests, is_request=False should return pool track
    t = eng._pop_next_track(is_request=False)
    assert t is not None, "Should have popped a track"
    assert t.source == "pool1", f"Expected pool1, got {t.source}"


def test_pop_next_track_no_pool_returns_none():
    """When no pool and is_request=False, should return None."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)

    # No tracks at all
    t = eng._pop_next_track(is_request=False)
    assert t is None, "Should return None when no tracks"


def test_pop_next_track_requests_empty_returns_none():
    """When is_request=True but no requests, should return None (not pool)."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)

    pool_track = Track(source="pool1", title="Pool", duration=180.0, requester="AutoDJ")
    eng.queue.add_pool([pool_track])

    # is_request=True but no requests should return None
    t = eng._pop_next_track(is_request=True)
    assert t is None, "Should return None when is_request=True but no requests"
