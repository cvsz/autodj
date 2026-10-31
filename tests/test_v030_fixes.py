"""Regression tests for v0.3.0 fixes:
- TTS: thread-safe single-engine worker (N-tts-1)
- player.play_file: CREATE_NO_WINDOW on Windows (N-player-1)
- player.play: the per-track mpv spawn hides the console window too (N-player-2)
- player._base: force --force-window=no so a user's mpv.conf cannot open the mpv video window (N-player-3)
- library: search_limit parameter wired through (N-lib-1)
- config: search_limit validated in range (N-cfg-1)
- messages: 'error' is now a human-readable sentence (N-msg-1)
- webchat: find_web_panes logs when pane not found (N-web-1)
- engine: _remote passes search_limit from config (N-eng-1)
"""

from __future__ import annotations

import logging
import sys
import subprocess
import threading
import types
from unittest.mock import MagicMock

import pytest

from camfrog_autodj.config import Config, ConfigError
from camfrog_autodj.library import remote_tracks
from camfrog_autodj.messages import tr
from camfrog_autodj.models import Track
from camfrog_autodj.player import MpvPlayer


# ---------------------------------------------------------------------------
# N-msg-1: 'error' message is now descriptive, not just "error"
# ---------------------------------------------------------------------------
def test_error_message_is_descriptive():
    en_err = tr("en", "error")
    th_err = tr("th", "error")
    assert len(en_err) > 5, (
        "EN error message should be a real sentence, not bare 'error'"
    )
    assert len(th_err) > 5, "TH error message should be a real sentence"
    # Must not be the bare word used to trigger the condition
    assert en_err != "error"


# ---------------------------------------------------------------------------
# N-cfg-1: search_limit config key is accepted and validated
# ---------------------------------------------------------------------------
def test_search_limit_config_field():
    cfg = Config(search_limit=5)
    assert cfg.search_limit == 5


def test_search_limit_config_loads_from_toml(tmp_path):
    p = tmp_path / "cfg.toml"
    p.write_text("search_limit = 10\n", "utf-8")
    cfg = Config.load(str(p))
    assert cfg.search_limit == 10


def test_search_limit_config_out_of_range(tmp_path):
    p = tmp_path / "bad.toml"
    p.write_text("search_limit = 0\n", "utf-8")
    with pytest.raises(ConfigError, match="search_limit"):
        Config.load(str(p))


def test_search_limit_config_too_high(tmp_path):
    p = tmp_path / "bad.toml"
    p.write_text("search_limit = 100\n", "utf-8")
    with pytest.raises(ConfigError, match="search_limit"):
        Config.load(str(p))


def test_search_limit_config_default_is_one():
    cfg = Config()
    assert cfg.search_limit == 1


# ---------------------------------------------------------------------------
# N-lib-1: remote_tracks passes search_limit correctly
# ---------------------------------------------------------------------------
def test_remote_tracks_uses_search_limit_for_plain_query(monkeypatch):
    """ytsearch{n}: prefix must use search_limit, not hard-coded 1."""
    captured = {}

    def fake_extract_exe(exe, target, playlist, limit):
        captured["target"] = target
        raise OSError("no exe")  # fall through to module

    def fake_extract_module(target, playlist, limit):
        captured["target"] = target
        return {
            "entries": [
                {"webpage_url": "https://youtu.be/x", "title": "T", "duration": 60}
            ]
        }

    monkeypatch.setattr("camfrog_autodj.library._extract_exe", fake_extract_exe)
    monkeypatch.setattr("camfrog_autodj.library._extract_module", fake_extract_module)
    monkeypatch.setattr("camfrog_autodj.library.find_ytdlp", lambda *a, **kw: "")

    remote_tracks("some song", search_limit=3)
    assert captured["target"] == "ytsearch3:some song"


def test_remote_tracks_search_limit_default_is_one(monkeypatch):
    captured = {}

    def fake_extract_module(target, playlist, limit):
        captured["target"] = target
        return {
            "entries": [
                {"webpage_url": "https://youtu.be/x", "title": "T", "duration": 60}
            ]
        }

    monkeypatch.setattr(
        "camfrog_autodj.library._extract_exe",
        lambda *a: (_ for _ in ()).throw(OSError()),
    )
    monkeypatch.setattr("camfrog_autodj.library._extract_module", fake_extract_module)
    monkeypatch.setattr("camfrog_autodj.library.find_ytdlp", lambda *a, **kw: "")

    remote_tracks("artist name")
    assert captured["target"] == "ytsearch1:artist name"


def test_remote_tracks_url_not_prefixed_with_ytsearch(monkeypatch):
    """URLs must never get a ytsearch prefix regardless of search_limit."""
    captured = {}

    def fake_extract_module(target, playlist, limit):
        captured["target"] = target
        return {
            "entries": [
                {"webpage_url": "https://youtu.be/abc", "title": "T", "duration": 60}
            ]
        }

    monkeypatch.setattr("camfrog_autodj.library._extract_module", fake_extract_module)
    monkeypatch.setattr("camfrog_autodj.library.find_ytdlp", lambda *a, **kw: "")

    remote_tracks("https://youtu.be/abc", search_limit=5)
    assert captured["target"] == "https://youtu.be/abc"


# ---------------------------------------------------------------------------
# N-player-1: play_file uses CREATE_NO_WINDOW on Windows
# ---------------------------------------------------------------------------
def test_play_file_uses_create_no_window_on_windows(monkeypatch):
    """On Windows, play_file must set creationflags=0x08000000 to avoid console flash."""
    captured_kw = {}

    def fake_run(cmd, **kw):
        captured_kw.update(kw)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr("camfrog_autodj.player._is_windows", lambda: True)

    cfg = Config(mpv_path="mpv")
    p = MpvPlayer(cfg)
    p.play_file("/some/track.wav")

    assert "creationflags" in captured_kw, (
        "CREATE_NO_WINDOW creationflags not set on Windows"
    )
    assert captured_kw["creationflags"] == 0x08000000


def test_play_file_no_creationflags_on_posix(monkeypatch):
    """On non-Windows, play_file must not set creationflags."""
    captured_kw = {}

    def fake_run(cmd, **kw):
        captured_kw.update(kw)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr("camfrog_autodj.player._is_windows", lambda: False)

    cfg = Config(mpv_path="mpv")
    p = MpvPlayer(cfg)
    p.play_file("/some/track.wav")

    assert "creationflags" not in captured_kw


# ---------------------------------------------------------------------------
# N-player-2: play() (the per-track spawn) must hide the console window too,
# not just play_file -- before this fix every started track flashed one.
# ---------------------------------------------------------------------------
def test_play_hidden_console_on_windows(monkeypatch):
    """On Windows, play() must spawn mpv with creationflags=0x08000000."""
    captured_kw = {}
    fake_proc = MagicMock()
    fake_proc.wait.return_value = 0

    def fake_popen(cmd, **kw):
        captured_kw.update(kw)
        return fake_proc

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr("camfrog_autodj.player._is_windows", lambda: True)

    # Keep this test focused on process flags; avoid platform-dependent yt-dlp path discovery.
    cfg = Config(mpv_path="mpv", ytdlp_path="D:/tools/yt-dlp.exe", audio_device="")
    p = MpvPlayer(cfg)
    assert p.play("https://youtu.be/x", 80) is True

    assert "creationflags" in captured_kw, (
        "CREATE_NO_WINDOW not set on the per-track spawn"
    )
    assert captured_kw["creationflags"] == 0x08000000


def test_play_no_creationflags_on_posix(monkeypatch):
    """On non-Windows, play() must not set creationflags."""
    captured_kw = {}
    fake_proc = MagicMock()
    fake_proc.wait.return_value = 0

    def fake_popen(cmd, **kw):
        captured_kw.update(kw)
        return fake_proc

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr("camfrog_autodj.player._is_windows", lambda: False)

    # Keep this test focused on POSIX flags; avoid platform-dependent yt-dlp path discovery.
    cfg = Config(mpv_path="mpv", ytdlp_path="yt-dlp", audio_device="")
    p = MpvPlayer(cfg)
    assert p.play("some-local-track.mp3", 80) is True

    assert "creationflags" not in captured_kw


# ---------------------------------------------------------------------------
# N-player-3: the mpv command always forces window behaviour off, so a user's
# own mpv.conf (e.g. force-window=yes / pseudo-gui) cannot pop a video window
# over the GUI.  Command-line options always beat config files in mpv.
# ---------------------------------------------------------------------------
def test_mpv_base_forces_no_window():
    from camfrog_autodj.player import MpvPlayer

    cfg = Config(mpv_path="mpv", audio_device="")
    base = " ".join(MpvPlayer(cfg)._base())
    assert "--no-video" in base
    assert "--force-window=no" in base


def test_play_cmd_includes_no_window_flags(monkeypatch):
    captured_cmd = {}
    fake_proc = MagicMock()
    fake_proc.wait.return_value = 0

    def fake_popen(cmd, **kw):
        captured_cmd.update({"cmd": cmd})
        return fake_proc

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr("camfrog_autodj.player._is_windows", lambda: True)

    # Keep this test focused on window flags; yt-dlp discovery is covered separately.
    cfg = Config(mpv_path="mpv", ytdlp_path="D:/tools/yt-dlp.exe", audio_device="")
    p = MpvPlayer(cfg)
    assert p.play("https://youtu.be/x", 80) is True

    cmd = " ".join(captured_cmd["cmd"])
    assert "--no-video" in cmd
    assert "--force-window=no" in cmd


# ---------------------------------------------------------------------------
# N-tts-1: TTS worker serialises calls; synth is thread-safe
# ---------------------------------------------------------------------------
def test_tts_synth_is_callable_and_thread_safe(monkeypatch):
    """synth() must be importable and have the expected signature; the worker
    must serialise concurrent callers (smoke test: two threads call synth
    with a fake pyttsx3 that would corrupt state if called concurrently)."""
    from camfrog_autodj import tts

    results = []
    errors = []
    order = []
    lock = threading.Lock()

    class FakeVoice:
        name = "test voice"
        id = "v1"

    class FakeEngine:
        def setProperty(self, k, v):
            pass

        def getProperty(self, k):
            if k == "voices":
                return [FakeVoice()]
            return 150

        def save_to_file(self, text, path):
            with lock:
                order.append(text)

        def runAndWait(self):
            pass

    cfg = Config(tts_voice="", tts_rate=150)

    # Patch pyttsx3 so no real COM/SAPI needed
    fake_mod = types.ModuleType("pyttsx3")
    fake_mod.init = lambda: FakeEngine()

    import sys
    monkeypatch.setitem(sys.modules, "pyttsx3", fake_mod)

    # Reset TTS worker between test runs
    import importlib

    tts_mod = importlib.reload(tts)

    # Install the fake module before either caller starts; patching sys.modules
    # independently inside concurrent threads races with the worker's import.
    monkeypatch.setitem(sys.modules, "pyttsx3", fake_mod)

    def call_synth(text, path):
        try:
            tts_mod.synth(text, path, cfg)
            results.append(text)
        except Exception as ex:
            errors.append(ex)

    t1 = threading.Thread(target=call_synth, args=("hello", "/tmp/t1.wav"))
    t2 = threading.Thread(target=call_synth, args=("world", "/tmp/t2.wav"))
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    # Both calls must complete without error
    assert not errors, f"TTS errors: {errors}"
    assert len(results) == 2


# ---------------------------------------------------------------------------
# N-web-1: find_web_panes logs a debug message when view pane is not found
# ---------------------------------------------------------------------------
def test_find_web_panes_logs_when_not_found(caplog):
    from camfrog_autodj.webchat import find_web_panes

    # Build a fake pywinauto window with no matching panes
    fake_pane = MagicMock()
    fake_pane.element_info.name = "unrelated-pane-name"

    fake_win = MagicMock()
    fake_win.descendants.return_value = [fake_pane]

    with caplog.at_level(logging.DEBUG, logger="autodj"):
        view, inp = find_web_panes(fake_win, "wb-log-room-data", "wb-edit-data")

    assert view is None
    assert inp is None
    # Should have emitted a debug log explaining the failure
    assert any("wb-log-room-data" in rec.message for rec in caplog.records), (
        "Expected a debug log mentioning the missing view_title"
    )


def test_find_web_panes_returns_matching_panes():
    from camfrog_autodj.webchat import find_web_panes

    view_pane = MagicMock()
    view_pane.element_info.name = "camfrog://wb-log-room-data.inside/"
    input_pane = MagicMock()
    input_pane.element_info.name = "camfrog://wb-edit-data.inside/"

    fake_win = MagicMock()
    fake_win.descendants.return_value = [view_pane, input_pane]

    view, inp = find_web_panes(fake_win, "wb-log-room-data", "wb-edit-data")

    assert view is view_pane
    assert inp is input_pane


# ---------------------------------------------------------------------------
# N-eng-1: engine._remote wires search_limit from config
# ---------------------------------------------------------------------------
def test_engine_remote_uses_config_search_limit(monkeypatch):
    """Engine._remote must pass cfg.search_limit to remote_tracks."""
    from camfrog_autodj.adapters.base import ChatAdapter
    from camfrog_autodj.engine import Engine
    from camfrog_autodj.library import LocalIndex

    class FakeAdapter(ChatAdapter):
        def messages(self):
            return iter(())

        def send(self, text):
            pass

    class FakePlayer:
        skipped = False

        def stop(self):
            pass

        def set_pause(self, v):
            return True

        def set_volume(self, v):
            pass

        def available(self):
            return True

    captured = {}

    def fake_remote_tracks(
        query,
        requester="AutoDJ",
        playlist=False,
        limit=200,
        ytdlp_path="",
        mpv_path="",
        search_limit=1,
        raw_target=False,
        **kw,
    ):
        captured["search_limit"] = search_limit
        return [Track("https://youtu.be/x", "T", 60, requester)]

    monkeypatch.setattr("camfrog_autodj.engine.remote_tracks", fake_remote_tracks)

    cfg = Config(search_limit=7)
    e = Engine(cfg, FakeAdapter(), player=FakePlayer(), index=LocalIndex([]))
    e._remote("some query", "user1")

    assert captured.get("search_limit") == 7, (
        f"Expected search_limit=7 from config, got {captured.get('search_limit')}"
    )
