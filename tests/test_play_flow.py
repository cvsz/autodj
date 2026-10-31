"""Flow tests for user-request path fixes:

- scheme-less URL (youtube.com/..., youtu.be/x) is normalized with https:// before the remote lookup
- resolve("") raises UserError instead of searching the library
- bad msg_now / msg_next template falls back to built-in text (never kills the player-loop thread)
- play() passes the resolved yt-dlp to mpv via --script-opts=ytdl_hook-ytdl_path even when ytdlp_path=""
- playlist.json store: missing/corrupt file = empty, never fatal; appends are deduplicated by source
- engine.recent_requests + the `!last` command are registered
"""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock

import pytest

from camfrog_autodj.commands import COMMANDS
from camfrog_autodj.config import Config
from camfrog_autodj.engine import Engine
from camfrog_autodj.messages import tr
from camfrog_autodj.models import Track, UserError
from camfrog_autodj.player import MpvPlayer
from camfrog_autodj.playlist import PlaylistStore, load_playlist


class FakeIndex:
    """Library stub: find() never hits so resolve() always reaches _remote()."""

    def scan(self):
        pass

    def find(self, q, user):
        return None

    def contains(self, p):
        return False


class FakeAdapter:
    def messages(self):
        return iter(())

    def send(self, text):
        pass

    def close(self):
        pass


def make_engine(**cfgkw):
    cfg = Config(**cfgkw)
    return Engine(cfg, FakeAdapter(), index=FakeIndex())


def fake_remote(query, user="AutoDJ", playlist=False, search_limit=None, **kw):
    return []


# ---------------------------------------------------------------- resolve ---
def test_resolve_scheme_less_youtube_url(monkeypatch):
    e = make_engine()
    captured = {}
    monkeypatch.setattr(
        e,
        "_remote",
        lambda q, u="AutoDJ", playlist=False, search_limit=None, **kw: (
            captured.update(q=q) or []
        ),
    )
    e.resolve("www.youtube.com/watch?v=abc", "user1", False)
    assert captured["q"] == "https://www.youtube.com/watch?v=abc"


def test_resolve_youtu_be_without_scheme(monkeypatch):
    e = make_engine()
    captured = {}
    monkeypatch.setattr(
        e,
        "_remote",
        lambda q, u="AutoDJ", playlist=False, search_limit=None, **kw: (
            captured.update(q=q) or []
        ),
    )
    e.resolve("youtu.be/xyz", "user1", True)
    assert captured["q"] == "https://youtu.be/xyz"


def test_resolve_empty_arg_raises_nothing_found():
    e = make_engine()
    with pytest.raises(UserError, match="nothing found"):
        e.resolve("   ", "user1", False)


# ------------------------------------------------------------- announce ----
def test_fmt_now_bad_template_falls_back_to_builtin():
    e = make_engine(msg_now="Now playing {artist} - {title}")
    out = e.fmt_now(Track("s", "T", 60, "u"))
    assert "T" in out
    assert "{artist}" not in out


def test_fmt_next_bad_template_falls_back_to_builtin():
    e = make_engine(msg_next="Up next {artist} - {title}")
    out = e.fmt_next(Track("s", "T", 60, "u"))
    assert "T" in out
    assert "{artist}" not in out


# --------------------------------------------------------- player ytdl hook -
def test_play_includes_resolved_ytdlp_hook_even_when_ytdlp_path_empty(monkeypatch):
    captured = {}
    proc = MagicMock()
    proc.wait.return_value = 0

    def fake_popen(cmd, **kw):
        captured["cmd"] = list(cmd)
        return proc

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr("camfrog_autodj.player._is_windows", lambda: True)
    monkeypatch.setattr(
        "camfrog_autodj.player.find_ytdlp", lambda *a, **kw: "D:/tools/yt-dlp.exe"
    )

    cfg = Config(mpv_path="mpv", ytdlp_path="")
    assert MpvPlayer(cfg).play("https://youtu.be/abc", 80) is True
    assert any(
        "ytdl_hook-ytdl_path=D:/tools/yt-dlp.exe" in c for c in captured["cmd"]
    ), captured["cmd"]


# ------------------------------------------------------------- mpv timeout ---
def test_play_terminates_hung_mpv_after_timeout(monkeypatch):
    """mpv that never exits must be terminated after mpv_timeout, not block the player loop forever."""
    import time
    from camfrog_autodj.player import MpvPlayer

    killed = []
    fake_proc = MagicMock()
    calls = 0

    def mock_wait(timeout=None):
        nonlocal calls
        calls += 1
        if calls == 1:
            time.sleep(0.05)
            raise subprocess.TimeoutExpired("mpv", 0.01)
        return 0

    fake_proc.wait = mock_wait
    fake_proc.terminate = lambda: killed.append("terminate")
    fake_proc.kill = lambda: killed.append("kill")

    def fake_popen(cmd, **kw):
        return fake_proc

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr("camfrog_autodj.player._is_windows", lambda: True)
    monkeypatch.setattr(
        "camfrog_autodj.player.find_ytdlp", lambda *a, **kw: "D:/tools/yt-dlp.exe"
    )

    cfg = Config(mpv_path="mpv", ytdlp_path="", mpv_timeout=1)
    player = MpvPlayer(cfg)
    monkeypatch.setattr(player, "_played", lambda started: 2.0)
    assert player.play("https://youtu.be/abc", 80, duration=0.5) is False
    assert killed == ["terminate"], f"expected terminate, got {killed}"


# ----------------------------------------------------------- playlist.json --
def test_playlist_missing_file_is_empty(tmp_path):
    s = PlaylistStore(str(tmp_path / "does-not-exist.json"))
    assert s.load() == []


def test_playlist_add_persists_and_dedupes(tmp_path):
    p = str(tmp_path / "playlist.json")
    s = PlaylistStore(p)
    assert s.add([Track("https://youtu.be/a", "A", 10, "u1")]) == 1
    assert s.add([Track("https://youtu.be/a", "A", 10, "u1")]) == 0  # dedup by source
    assert s.add([Track("https://youtu.be/b", "B", 20, "u2")]) == 1
    tracks = s.load()
    assert [t.source for t in tracks] == ["https://youtu.be/a", "https://youtu.be/b"]
    assert tracks[0].requester == "u1" and getattr(tracks[0], "added", "")
    data = json.loads((tmp_path / "playlist.json").read_text("utf-8"))
    assert data["tracks"][1]["added_by"] == "u2"


def test_playlist_empty_path_is_noop():
    s = PlaylistStore("")
    assert s.add([Track("https://youtu.be/a", "A", 10, "u1")]) == 0


def test_playlist_corrupt_file_is_empty(tmp_path):
    p = tmp_path / "playlist.json"
    p.write_text("{broken json", "utf-8")
    assert load_playlist(str(p)) == []


# ---------------------------------------------------------- !last command --
def test_last_command_registered():
    assert "last" in COMMANDS and COMMANDS["last"][1] is False


def test_engine_recent_requests(tmp_path):
    p = str(tmp_path / "playlist.json")
    e = make_engine(playlist_file=p)
    e.playlist.add([Track("https://youtu.be/a", "A", 10, "u1")])
    e.playlist.add([Track("https://youtu.be/b", "B", 20, "u2")])
    items = e.recent_requests(5)
    assert [t.title for t in items] == ["A", "B"]
    assert items[0].requester == "u1"


def test_thai_messages_have_requested_keys():
    assert tr("th", "requested_none") == "ยังไม่มีประวัติการขอเพลง"
    assert tr("th", "last_head") == "ขอเพลงล่าสุด: "
    assert tr("en", "requested_none") == "No requests saved yet."
    assert tr("en", "last_head") == "Recently requested: "
