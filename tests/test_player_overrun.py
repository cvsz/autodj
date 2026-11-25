"""A requested song that runs past "length + grace" is not cut off or logged FAILED.

Live 2026-11-25: requests that had played to the end were logged FAILED
("mpv still running 30s after the expected end ... exited with code 1"). The grace
clock starts when mpv is launched, but yt-dlp resolves the URL for several seconds
before audio starts and streams buffer, so the song could still be playing its last
seconds; the position was read through the GUI's 0.15 s cached query, returned
nothing from a busy mpv, and the song was killed and counted as failed.
"""

from __future__ import annotations

import pytest

from autodj import player as player_mod
from autodj.player import MAX_OVERRUN_EXTENSIONS, MpvPlayer


class _Cfg:
    mpv_path = "mpv/mpv.exe"
    audio_device = ""
    audio_fade = False
    audio_fade_in_sec = 0.0
    mpv_timeout = 30.0


class _Proc:
    terminated = False

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return 0

    def kill(self):
        pass


@pytest.fixture
def run(monkeypatch):
    """play() a 302 s track with scripted waits, IPC answers and played time."""

    def _run(waits, answers, played=0.0, duration=302.0):
        p = MpvPlayer(_Cfg())
        proc = _Proc()
        waits = list(waits)
        queries: list[str] = []
        answers = {k: list(v) for k, v in answers.items()}

        def cmd_get(*cmd, **_kw):
            prop = cmd[-1]
            queries.append(prop)
            seq = answers.get(prop, [None])
            return seq.pop(0) if len(seq) > 1 else seq[0]

        monkeypatch.setattr("autodj.player.subprocess.Popen", lambda *a, **k: proc)
        monkeypatch.setattr(player_mod.time, "sleep", lambda s: None)
        monkeypatch.setattr(p, "_wait_for_mpv_end", lambda *a: waits.pop(0))
        monkeypatch.setattr(p, "_cmd_get", cmd_get)
        monkeypatch.setattr(p, "_played", lambda started: played)
        monkeypatch.setattr(MpvPlayer, "_report", lambda *a: None)
        ok = p.play("https://youtu.be/x", 100, duration=duration)
        return ok, proc, queries, len(waits)

    return _run


def test_still_playing_gets_more_time_instead_of_being_killed(run, caplog):
    # Grace ran out at 290 s of 302 s and the position advances: wait, then mpv exits
    # by itself (code 1 at the end of a stream, after the whole song played).
    with caplog.at_level("INFO", logger="autodj"):
        ok, proc, _q, left = run(
            waits=[(None, True), (1, False)],
            answers={"time-pos": [290.0, 291.0]},
            played=303.0,
        )
    assert ok is True and not proc.terminated and left == 0
    assert "mpv still playing https://youtu.be/x with 11 s left" in caplog.text
    assert "checking position" not in caplog.text


def test_mpv_that_does_not_answer_is_still_a_hang(run, caplog):
    # No IPC answer within 2 s: mpv itself is stuck; that remains a failure.
    with caplog.at_level("INFO", logger="autodj"):
        ok, proc, _q, _ = run(waits=[(None, True)], answers={}, played=335.0)
    assert ok is False and proc.terminated
    assert "mpv did not answer for https://youtu.be/x: treating it as hung" in caplog.text


def test_eof_reached_counts_as_completed(run):
    ok, proc, _q, _ = run(
        waits=[(None, True)], answers={"time-pos": [150.0, 150.0, 150.0], "eof-reached": [True]}
    )
    assert ok is True and proc.terminated


def test_stalled_short_of_the_end_is_still_a_failure(run, caplog):
    # Position does not move and the end was not reached: a real hang.
    with caplog.at_level("INFO", logger="autodj"):
        ok, proc, _q, _ = run(
            waits=[(None, True)],
            answers={"time-pos": [100.0, 100.0, 100.0], "eof-reached": [False]},
            played=340.0,
        )
    assert ok is False and proc.terminated
    assert "mpv stopped at 100 of 302 s" in caplog.text


def test_extensions_are_bounded(run):
    waits = [(None, True)] * (MAX_OVERRUN_EXTENSIONS + 1)
    pos = [float(n) for n in range(100, 100 + 2 * MAX_OVERRUN_EXTENSIONS + 2)]
    ok, proc, _q, left = run(
        waits=waits, answers={"time-pos": pos, "eof-reached": [False]}, played=400.0
    )
    assert left == 0  # one initial wait + MAX_OVERRUN_EXTENSIONS extensions, no more
    assert proc.terminated and ok is False
