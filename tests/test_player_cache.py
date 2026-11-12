"""Tests for MpvPlayer.get_time_pos() position caching.

The GUI polls playback position every 500 ms. Without the cache each poll opens
and closes a new mpv IPC connection (named pipe on Windows, Unix socket on
Linux), so the cache avoids that repeated IPC while keeping the progress bar
current.
"""

import time

from camfrog_autodj.player import _POS_CACHE_TTL, MpvPlayer


class _Cfg:
    mpv_path = "mpv/mpv.exe"
    audio_device = "auto"


def _make_player(monkeypatch):
    player = MpvPlayer(_Cfg())
    calls: list[tuple] = []

    def fake_cmd_get(*cmd):
        calls.append(cmd)
        return float(len(calls)) * 10.0

    monkeypatch.setattr(player, "_cmd_get", fake_cmd_get)
    return player, calls


def test_get_time_pos_queries_ipc_once_then_caches(monkeypatch):
    player, calls = _make_player(monkeypatch)
    assert player.get_time_pos() == 10.0
    assert player.get_time_pos() == 10.0  # served from cache, no new IPC
    assert len(calls) == 1


def test_get_time_pos_refreshes_after_ttl(monkeypatch):
    player, calls = _make_player(monkeypatch)
    player.get_time_pos()  # populate the cache
    assert len(calls) == 1
    # Stale-cache simulation: force a re-query past the TTL boundary.
    with player._lock:
        player._pos_cache = (10.0, time.monotonic() - _POS_CACHE_TTL - 0.1)
    assert player.get_time_pos() == 20.0
    assert len(calls) == 2


def test_get_time_pos_invalidated_on_seek_stop(monkeypatch):
    player, calls = _make_player(monkeypatch)
    player.get_time_pos()
    assert len(calls) == 1
    # seek() attempts IPC (no pipe set up -> returns False) but must invalidate
    # the cache so the next read re-queries.
    assert player.seek(3) is False
    assert player.get_time_pos() == 20.0
    assert len(calls) == 2
    # stop() also invalidates the cache (no track -> no position).
    player.stop()
    assert player.get_time_pos() == 30.0
    assert len(calls) == 3
