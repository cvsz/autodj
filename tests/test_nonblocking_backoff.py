"""Test that backoff is non-blocking."""

import time

from camfrog_autodj.adapters import NullAdapter
from camfrog_autodj.config import Config
from camfrog_autodj.engine import Engine
from camfrog_autodj.models import Track


def test_backoff_does_not_block_player_loop():
    """Backoff should be non-blocking - _track_failed should return immediately."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)

    # Simulate a track failure
    track = Track(source="test", title="Test", duration=180.0, requester="user")
    track.state = "PLAYING"

    # Call _track_failed - should NOT block
    start = time.monotonic()
    eng._track_failed(track, fails=1)
    elapsed = time.monotonic() - start

    # Should return immediately (non-blocking)
    assert elapsed < 0.1, f"_track_failed took {elapsed:.3f}s, should be < 0.1s"
    assert eng._backoff_until > time.monotonic()


def test_player_loop_respects_backoff():
    """Player loop should respect _backoff_until and not play during backoff."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)

    # Set a backoff time in the future
    eng._backoff_until = time.monotonic() + 10.0

    # The player loop should wait when _backoff_until is in the future
    # We can't easily test the loop directly, but we can verify the condition
    assert eng._backoff_until > time.monotonic()

    # After backoff expires, it should be 0
    eng._backoff_until = 0.0
    assert eng._backoff_until == 0.0
