"""A full play ending with mpv exit code 1 is a completed track; failures stay out of the room."""

import time
from types import SimpleNamespace

from camfrog_autodj.adapters import NullAdapter
from camfrog_autodj.config import Config
from camfrog_autodj.engine import Engine
from camfrog_autodj.models import Track
from camfrog_autodj.player import MpvPlayer


def _player(monkeypatch, played_s: float, rc: int):
    p = MpvPlayer(SimpleNamespace(mpv_path="mpv", audio_device="", mpv_timeout=30, volume=50))
    monkeypatch.setattr(p, "available", lambda: True, raising=False)

    class _Proc:
        pid = 1

        def wait(self, timeout=None):
            return rc

    import camfrog_autodj.player as player_mod

    monkeypatch.setattr(player_mod.subprocess, "Popen", lambda *a, **k: _Proc())
    monkeypatch.setattr(p, "_wait_for_mpv_end", lambda proc, started, limit: (rc, False))
    monkeypatch.setattr(p, "_played", lambda started: played_s)
    monkeypatch.setattr(p, "_report", lambda *a, **k: None)
    return p


def test_exit_code_1_after_full_play_is_completed(monkeypatch):
    p = _player(monkeypatch, played_s=276.0, rc=1)
    assert p.play("https://youtu.be/x", 50, 276.0) is True


def test_exit_code_1_early_is_still_a_failure(monkeypatch):
    p = _player(monkeypatch, played_s=10.0, rc=1)
    assert p.play("https://youtu.be/x", 50, 276.0) is False


def test_failed_track_is_not_announced_in_room():
    e = Engine(Config(), NullAdapter())
    said: list[str] = []
    e.say = lambda text, *a, **k: said.append(text) or True  # type: ignore[method-assign]
    e._track_failed(Track("u", "Song", 10, "amy"), 1)
    assert not any("Song" in s for s in said)
    assert time.monotonic() <= e._backoff_until + 60  # back-off still applied
