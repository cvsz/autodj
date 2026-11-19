"""mpv is tied to AutoDJ's lifetime: killing AutoDJ kills mpv (Windows Job Object)."""

import subprocess
import sys
import time

import pytest

from autodj import winjob


def test_no_op_off_windows(monkeypatch):
    monkeypatch.setattr(winjob.sys, "platform", "linux")
    assert winjob.kill_with_parent(object()) is False  # type: ignore[arg-type]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Job Objects")
def test_child_dies_when_parent_is_force_killed():
    """A parent that ties a long-running child to itself, then is killed with /F."""
    parent_code = (
        "import subprocess, sys, time; from autodj.winjob import kill_with_parent; "
        "c = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
        "print(c.pid, kill_with_parent(c), flush=True); time.sleep(60)"
    )
    parent = subprocess.Popen(
        [sys.executable, "-c", parent_code], stdout=subprocess.PIPE, text=True
    )
    try:
        child_pid, attached = parent.stdout.readline().split()
        assert attached == "True"
        subprocess.run(["taskkill", "/F", "/PID", str(parent.pid)], capture_output=True)
        parent.wait(10)
        deadline = time.monotonic() + 5
        alive = True
        while time.monotonic() < deadline:
            out = subprocess.run(
                ["tasklist", "/FI", f"PID eq {child_pid}", "/NH"], capture_output=True, text=True
            ).stdout
            alive = child_pid in out
            if not alive:
                break
            time.sleep(0.2)
        if alive:
            subprocess.run(["taskkill", "/F", "/PID", child_pid], capture_output=True)
        assert not alive, "child outlived its force-killed parent"
    finally:
        if parent.poll() is None:
            parent.kill()


def test_player_ties_mpv_to_autodj(monkeypatch):
    """MpvPlayer.play passes the mpv Popen to kill_with_parent."""
    from types import SimpleNamespace

    import autodj.player as player_mod

    tied = []
    monkeypatch.setattr(player_mod, "kill_with_parent", lambda p: tied.append(p) or True)

    class _Proc:
        pid = 1

        def poll(self):
            return 0

        def wait(self, timeout=None):
            return 0

    proc = _Proc()
    monkeypatch.setattr(player_mod.subprocess, "Popen", lambda *a, **k: proc)
    p = player_mod.MpvPlayer(
        SimpleNamespace(mpv_path="mpv", audio_device="", mpv_timeout=30, volume=50)
    )
    monkeypatch.setattr(p, "available", lambda: True, raising=False)
    monkeypatch.setattr(p, "_wait_for_mpv_end", lambda pr, started, limit: (0, False))
    monkeypatch.setattr(p, "_report", lambda *a, **k: None)
    p.play("https://youtu.be/x", 50, 10.0)
    assert tied == [proc]
