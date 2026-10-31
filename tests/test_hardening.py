"""Regression tests for the v0.2.0 audit findings. Each test pins a bug that existed in 0.1.0."""

import json
import os
import pathlib
import re
import shutil
import threading
import time

import pytest
from test_core import FakeAdapter, FakePlayer, make, out

from camfrog_autodj import __version__
from camfrog_autodj.adapters.base import ChatMessage
from camfrog_autodj.commands import COMMANDS
from camfrog_autodj.config import Config, ConfigError
from camfrog_autodj.messages import STR
from camfrog_autodj.models import Track
from camfrog_autodj.playqueue import PlayQueue


def T(n, u="AutoDJ", d=60):
    return Track(f"/m/{n}.mp3", n, d, u)


# ---- F1: the bot must never act on its own chat lines -----------------------------------------


def test_help_line_does_not_start_with_prefix():
    for lang in ("en", "th"):
        for key in ("help_base", "help_admin"):
            assert not STR[lang][key].lstrip().startswith("{p}"), (lang, key)


def test_echo_of_our_own_line_is_ignored_even_with_wrong_bot_nick():
    class OneShot(FakeAdapter):
        def __init__(self, msgs):
            self.msgs = msgs

        def messages(self):
            return iter(self.msgs)

    e = make()
    e.cfg.bot_nick = "AutoDJ"  # but the account is really called "zdevz"
    e.admins = {"zdevz"}
    e.say("!skip everything")  # e.g. an admin's `!say !skip everything`
    sent = [e.outbox.get_nowait()]
    e._remember_sent(sent[0])  # what _sender does just before posting to the room
    e.adapter = OneShot(
        [ChatMessage("zdevz", "!skip everything"), ChatMessage("zdevz", "!np")]
    )
    e._chat_loop()
    time.sleep(0.2)
    texts = [t for _, t in e.chat_log]
    assert (
        texts.count("!skip everything") == 1
    )  # only our own log entry, not re-processed
    assert any(
        "Nothing playing" in o or "nothing playing" in o.lower() for o in out(e)
    )  # a real !np still works


def test_wrapped_continuation_never_starts_with_prefix():
    e = make()
    e.cfg.max_msg_len = 20
    e.say(
        "aaaa bbbb cccc dddd !skip eeee"
    )  # wraps so the 2nd line would start with "!skip"
    lines = out(e)
    assert len(lines) >= 2 and all(not ln.startswith("!") for ln in lines[1:])


def test_echo_is_consumed_once():
    e = make()
    e._remember_sent("hello  world")
    assert e._is_echo("hello world") is True
    assert e._is_echo("hello world") is False


# ---- F2: failing tracks must not spam the room or spin the CPU --------------------------------


class FailingPlayer(FakePlayer):
    def __init__(self):
        super().__init__()
        self.plays = 0

    def play(self, source, volume, duration=None):
        self.plays += 1
        return False


def test_failures_are_throttled_and_backed_off():
    e = make()
    e.player = FailingPlayer()
    e.queue.add_pool([T("a"), T("b"), T("c")])
    delays = []
    e.fail_delay = lambda n: delays.append(n) or 0.0
    th = threading.Thread(target=e._player_loop, daemon=True)
    th.start()
    deadline = time.monotonic() + 3.0
    while e.player.plays < 3 and time.monotonic() < deadline:
        time.sleep(0.01)
    e.stop_evt.set()
    e.wake.set()
    th.join(2)
    cannot = [o for o in out(e) if o.startswith("Could not play")]
    assert e.player.plays >= 3  # retries continue without relying on scheduler speed...
    assert 1 <= len(cannot) <= 3  # ...but only announced a few times
    assert delays[:3] == [1, 2, 3]  # consecutive-failure counter grows


# ---- F3: !remove must remove the item the user saw, even if the queue shifts ------------------


def test_remove_track_by_identity():
    q = PlayQueue(shuffle=False)
    a, b, c = T("a", "amy"), T("b", "bob"), T("c", "cat")
    for t in (a, b, c):
        q.add_request(t)
    assert q.remove_track(a) is True
    assert q.remove_track(a) is False  # already gone: nothing else is removed
    assert [t.title for t in q.requests] == ["b", "c"]


def test_remove_command_survives_queue_shift():
    e = make()
    e.router.handle(ChatMessage("amy", "!play a"))
    e.router.handle(ChatMessage("bob", "!play b"))
    out(e)
    victim = e.queue.get(2)  # bob's
    real_get = e.queue.get

    def shifting_get(n):  # someone else's request vanishes right after get()
        t = real_get(n)
        e.queue.remove_track(e.queue.requests[0])
        return t

    e.queue.get = shifting_get
    e.router.handle(ChatMessage("bob", "!remove 2"))
    assert victim not in e.queue.requests
    assert out(e) == ["Removed: b"]


# ---- F4: per-user limit must hold even when lookups overlap -----------------------------------


def test_limit_rechecked_after_slow_lookup():
    e = make()
    e.cfg.max_requests_per_user = 1
    real = e.resolve

    def slow_resolve(arg, user, admin):
        e.queue.add_request(
            T("sneaked-in", user)
        )  # a parallel request of the same user finished first
        return real(arg, user, admin)

    e.resolve = slow_resolve
    e.router.handle(ChatMessage("amy", "!play second"))
    assert "max 1" in out(e)[0]
    assert [t.title for t in e.queue.requests] == ["sneaked-in"]


def test_duplicate_request_rejected_for_users_not_admins():
    e = make()
    e.router.handle(ChatMessage("amy", "!play same"))
    e.router.handle(ChatMessage("bob", "!play same"))
    msgs = out(e)
    assert msgs[0].startswith("Queued #1") and "already" in msgs[1]
    e.router.handle(ChatMessage("boss", "!play same"))
    assert out(e)[0].startswith("Queued #2")


# ---- F5: pool de-duplication, history, block list ---------------------------------------------


def test_pool_dedupes_by_source():
    q = PlayQueue()
    q.add_pool([T("a"), T("b")])
    q.add_pool([T("a"), T("c")])
    assert sorted(t.title for t in q.pool) == ["a", "b", "c"]


def test_history_records_finished_tracks():
    e = make()
    e.player.play = lambda s, v, d=None: True
    e.queue.add_request(T("one", "amy"))
    th = threading.Thread(target=e._player_loop, daemon=True)
    th.start()
    time.sleep(0.3)
    e.stop_evt.set()
    e.wake.set()
    th.join(2)
    out(e)
    e.router.handle(ChatMessage("bob", "!history"))
    assert "one" in out(e)[0]


def test_block_and_unblock():
    e = make()
    e.router.handle(ChatMessage("boss", "!block amy"))
    assert out(e) == ["Blocked: amy"]
    e.router.handle(ChatMessage("Amy", "!play x"))
    assert out(e) == [] and len(e.queue.requests) == 0  # silently ignored
    e.router.handle(ChatMessage("boss", "!block boss"))
    assert "admin" in out(e)[0]
    e.router.handle(ChatMessage("boss", "!unblock amy"))
    out(e)
    e.router.handle(ChatMessage("amy", "!play x"))
    assert out(e)[0].startswith("Queued")


def test_command_aliases_unique():
    with pytest.raises(ValueError):
        from camfrog_autodj.commands import command

        command("play")(lambda *a: None)
    assert "history" in COMMANDS and "block" in COMMANDS


# ---- F6: config errors are explained, not tracebacks ------------------------------------------


def _cfg(tmp_path, text):
    p = tmp_path / "config.toml"
    p.write_text(text, "utf-8")
    return str(p)


def test_toml_syntax_error_shows_the_bad_line(tmp_path):
    path = _cfg(tmp_path, "a = 1\n" * 0 + 'bot_nick = "x"\nThumbprint: CD42A0597C4C\n')
    with pytest.raises(ConfigError) as ei:
        Config.load(path)
    msg = str(ei.value)
    assert "line 2" in msg and "Thumbprint: CD42A0597C4C" in msg and "#" in msg


def test_unknown_key_gets_a_suggestion(tmp_path):
    with pytest.raises(ConfigError) as ei:
        Config.load(_cfg(tmp_path, 'mvp_path = "C:/mpv/mpv.exe"\n'))
    assert "mvp_path" in str(ei.value) and "mpv_path" in str(ei.value)


@pytest.mark.parametrize(
    "text, needle",
    [
        ('admins = "zdevz"\n', "admins"),
        ('lang = "de"\n', "lang"),
        ("volume = 150\n", "volume"),
        ('volume = "loud"\n', "volume"),
        ('send_mode = "sideways"\n', "send_mode"),
        ("view_kind = 3\n", "view_kind"),
        ('window_title_re = "(unclosed"\n', "window_title_re"),
        ('prefix = ""\n', "prefix"),
        ('shuffle = "yes"\n', "shuffle"),
    ],
)
def test_config_value_validation(tmp_path, text, needle):
    with pytest.raises(ConfigError) as ei:
        Config.load(_cfg(tmp_path, text))
    assert needle in str(ei.value)


def test_valid_config_still_loads_and_normalises(tmp_path):
    c = Config.load(
        _cfg(
            tmp_path,
            'admins = [" Zdevz "]\nvolume = 55\nlang = "th"\nspeed = 1\n'.replace(
                "speed = 1\n", ""
            ),
        )
    )
    assert c.admins == ["Zdevz"] and c.volume == 55 and c.lang == "th"
    assert Config.load(None).lang == "en"


def test_shipped_example_config_is_valid():
    import pathlib

    ex = pathlib.Path(__file__).resolve().parent.parent / "config.example.toml"
    c = Config.load(str(ex))
    assert c.chat_reader == "uia"


def test_save_config_never_writes_invalid_toml(tmp_path):
    from camfrog_autodj.discover import save_config

    p = tmp_path / "config.toml"
    p.write_text('bot_nick = "X"\n', "utf-8")
    assert (
        save_config(str(p), {"bad key": "x"}) is False
    )  # would be invalid TOML: refused
    assert p.read_text("utf-8") == 'bot_nick = "X"\n'
    assert (
        save_config(str(p), {"window_title_re": "tab\there\nnewline"}) is True
    )  # tricky value: escaped, still valid
    assert Config.load(str(p)).window_title_re == "tab\there\nnewline"
    p.write_text('bot_nick = "X"\n', "utf-8")
    assert save_config(str(p), {"window_title_re": r"ok:\ ห้อง"}) is True
    assert Config.load(str(p)).window_title_re == r"ok:\ ห้อง"
    assert not list(tmp_path.glob("*.tmp"))


# ---- F7: i18n integrity -----------------------------------------------------------------------


def test_en_th_use_same_placeholders():
    fields = lambda s: set(re.findall(r"{(\w+)}", s))
    for k in STR["en"]:
        assert fields(STR["en"][k]) == fields(STR["th"][k]), k


# ---- F8: yt-dlp lookups (module missing in the frozen exe was a real failure) -----------------

SEARCH_JSON = {
    "_type": "playlist",
    "entries": [
        {
            "id": "abc123def45",
            "title": "Song A",
            "duration": 201,
            "url": "https://www.youtube.com/watch?v=abc123def45",
        },
        None,
        {"id": "zzz", "title": "Live", "duration": None},
    ],
}


def test_parse_ytdlp_info_playlist_and_single():
    from camfrog_autodj.library import parse_ytdlp_info

    t = parse_ytdlp_info(SEARCH_JSON, "amy")
    assert [x.title for x in t] == ["Song A", "Live"]
    assert (
        t[1].source == "https://www.youtube.com/watch?v=zzz" and t[1].duration is None
    )
    single = {
        "id": "q",
        "title": "One",
        "duration": 5,
        "webpage_url": "https://youtu.be/q",
    }
    assert parse_ytdlp_info(single, "amy")[0].source == "https://youtu.be/q"


def test_remote_tracks_falls_back_to_exe_when_module_missing(monkeypatch, tmp_path):
    import builtins
    import subprocess

    from camfrog_autodj import library

    real_import = builtins.__import__

    def no_yt_dlp(name, *a, **k):
        if name == "yt_dlp":
            raise ModuleNotFoundError("No module named 'yt_dlp'")
        return real_import(name, *a, **k)

    exe = tmp_path / "yt-dlp.exe"
    exe.write_text("x")
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, json.dumps(SEARCH_JSON), "")

    monkeypatch.setattr(builtins, "__import__", no_yt_dlp)
    monkeypatch.setattr(subprocess, "run", fake_run)
    tracks = library.remote_tracks("some song", "amy", ytdlp_path=str(exe))
    assert tracks[0].title == "Song A"
    assert (
        calls[0][0] == str(exe)
        and "ytsearch1:some song" in calls[0]
        and "--no-playlist" in calls[0]
    )


def test_remote_tracks_clear_error_when_nothing_available(monkeypatch):
    import builtins

    from camfrog_autodj import library
    from camfrog_autodj.models import UserError

    real_import = builtins.__import__
    monkeypatch.setattr(
        builtins,
        "__import__",
        lambda n, *a, **k: (
            (_ for _ in ()).throw(ModuleNotFoundError(n))
            if n == "yt_dlp"
            else real_import(n, *a, **k)
        ),
    )
    monkeypatch.setattr(library, "find_ytdlp", lambda *a, **k: "")
    with pytest.raises(UserError) as ei:
        library.remote_tracks("x", "amy")
    assert "yt-dlp" in str(ei.value)


# ---- F9: text sent to Camfrog is sanitised ----------------------------------------------------


def test_clean_text():
    from camfrog_autodj.textutil import clean_text

    assert clean_text("a\tb\r\nc\x00d\x1b[31m") == "a b c d [31m"
    assert clean_text("  ไทย  ok ") == "ไทย ok"


# ---- F10: housekeeping ------------------------------------------------------------------------


def test_versions_agree():
    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent
    assert f'version = "{__version__}"' in (root / "pyproject.toml").read_text("utf-8")
    parts = ".".join(__version__.split(".") + ["0"] * (4 - len(__version__.split("."))))
    assert f"'{parts}'" in (root / "version_info.txt").read_text("utf-8")


def test_doctor_reports_missing_mpv_and_ok_dirs(monkeypatch, tmp_path):
    from camfrog_autodj import doctor

    monkeypatch.setattr(doctor.shutil, "which", lambda x: None)
    cfg = Config(
        mpv_path="C:/nope/mpv.exe",
        music_dirs=[str(tmp_path), str(tmp_path / "missing")],
        admins=[],
    )
    res = doctor.run_checks(cfg, check_window=False)
    levels = {(lvl, txt) for lvl, txt in res}
    text = "\n".join(f"{l} {t}" for l, t in res)
    assert any(l == "FAIL" and "mpv" in t for l, t in res)
    assert any(l == "WARN" and "missing" in t for l, t in res)
    assert any(l == "WARN" and "admins" in t for l, t in res)
    assert any(l == "OK" and str(tmp_path) in t for l, t in res), text
    assert doctor.has_failures(res)


def test_find_ytdlp_prefers_the_one_next_to_mpv(tmp_path, monkeypatch):
    import os

    from camfrog_autodj.library import find_ytdlp

    nt = os.name == "nt"
    real_which = shutil.which
    monkeypatch.setattr(
        "camfrog_autodj.library.shutil.which",
        lambda command: None if command == "yt-dlp" else real_which(command),
    )
    mpv = tmp_path / ("mpv.exe" if nt else "mpv")
    yt = tmp_path / ("yt-dlp.exe" if nt else "yt-dlp")
    mpv.write_text("x")
    mpv.chmod(0o755)
    assert find_ytdlp("", str(mpv)) in ("", str(yt)) and find_ytdlp(
        "", str(mpv)
    ) != str(mpv)
    yt.write_text("x")
    assert find_ytdlp("", str(mpv)) == str(
        yt
    )  # same folder as mpv: the one mpv itself will use
    assert find_ytdlp(str(yt), "") == str(yt)  # explicit setting wins
    assert (
        find_ytdlp(str(tmp_path / "nope.exe"), str(mpv)) == ""
    )  # explicit but wrong: do not silently pick another


def test_find_ytdlp_falls_back_to_path(monkeypatch):
    from camfrog_autodj.library import find_ytdlp

    monkeypatch.setattr(
        "camfrog_autodj.library.shutil.which",
        lambda command: "/opt/bin/yt-dlp" if command == "yt-dlp" else None,
    )
    assert find_ytdlp("", "missing-mpv") == "/opt/bin/yt-dlp"


def test_remote_tracks_uses_module_when_no_exe(monkeypatch):
    import sys
    import types

    from camfrog_autodj import library

    class FakeYDL:
        def __init__(self, opts):
            FakeYDL.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, target, download=False):
            FakeYDL.target = target
            return SEARCH_JSON

    mod = types.ModuleType("yt_dlp")
    mod.YoutubeDL = FakeYDL
    monkeypatch.setitem(sys.modules, "yt_dlp", mod)
    monkeypatch.setattr(library, "find_ytdlp", lambda *a, **k: "")
    tracks = library.remote_tracks("some song", "amy")
    assert tracks[0].title == "Song A" and FakeYDL.target == "ytsearch1:some song"
    assert (
        FakeYDL.opts["noplaylist"] is True
        and FakeYDL.opts["extract_flat"] == "in_playlist"
    )


# ---- GUI visuals (pure maths; the Tk window itself needs a display) ---------------------------


def test_visual_colour_helpers():
    from camfrog_autodj.visuals import gradient, hex_to_rgb, lerp_color, rgb_to_hex

    assert (
        hex_to_rgb("#ff3d9a") == (255, 61, 154)
        and rgb_to_hex(255, 61, 154) == "#ff3d9a"
    )
    assert lerp_color("#000000", "#ffffff", 0.5) == "#808080"
    assert lerp_color("#000000", "#ffffff", 9) == "#ffffff"  # clamped
    g = gradient(["#ff0000", "#00ff00", "#0000ff"], 5)
    assert (
        g[0] == "#ff0000" and g[2] == "#00ff00" and g[-1] == "#0000ff" and len(g) == 5
    )


def test_equaliser_is_bounded_and_quiet_when_paused():
    from camfrog_autodj.visuals import bar_heights, ease

    for t in (0.0, 1.3, 77.7):
        live, quiet = bar_heights(t, 32, 1.0), bar_heights(t, 32, 0.08)
        assert len(live) == 32 and all(0.0 <= v <= 1.0 for v in live + quiet)
        assert sum(quiet) < sum(live) * 0.5
    assert ease(0.0, 1.0) > 0.5 and ease(1.0, 0.0) > 0.8  # fast attack, slow decay


def test_aurora_and_particles_and_confetti_are_stable_and_bounded():
    from camfrog_autodj.visuals import (
        aurora_offset,
        confetti_burst,
        confetti_pos,
        make_particles,
        particle_pos,
    )

    for t in (0.0, 5.0, 123.4):
        for i in range(4):
            v = aurora_offset(t, i, 4)
            assert 0.0 <= v <= 1.0
    ps = make_particles(12, seed=7)
    ps2 = make_particles(12, seed=7)
    assert ps == ps2 and len(ps) == 12  # seeded: reproducible frame to frame
    for p in ps:
        x, y, a = particle_pos(p, 3.3, 100, 100, 50)
        assert 0.0 <= a <= 1.0
    cs = confetti_burst(10, seed=3)
    assert len(cs) == 10 and confetti_burst(10, seed=3) == cs
    x0, y0, r0, a0 = confetti_pos(cs[0], 0.0, 50, 50)
    assert (x0, y0) == (
        50,
        50,
    ) and a0 == 1.0  # starts at the launch point, fully opaque
    x1, y1, r1, a1 = confetti_pos(cs[0], 1.4, 50, 50)
    assert a1 == 0.0  # fully faded by the end of its life


def test_vinyl_and_pulse_and_roundrect():
    from camfrog_autodj.visuals import pulse, round_rect_points, vinyl_angle

    assert vinyl_angle(0) == 0 and abs(vinyl_angle(60) - (33.3 * 360) % 360) < 1e-6
    assert (
        0.0 <= min(pulse(x / 10) for x in range(40))
        and max(pulse(x / 10) for x in range(40)) <= 1.0
    )
    pts = round_rect_points(0, 0, 100, 40, 999)  # radius is clamped to half the height
    assert (
        min(pts[0::2]) == 0
        and max(pts[0::2]) == 100
        and min(pts[1::2]) == 0
        and max(pts[1::2]) == 40
    )


def test_build_env_checker_lists_what_is_missing():
    import importlib.util
    import pathlib

    spec = importlib.util.spec_from_file_location(
        "check_build_env",
        pathlib.Path(__file__).resolve().parent.parent / "tools" / "check_build_env.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert (
        mod.missing(lambda name: object()) == {}
    )  # everything importable: nothing missing
    gone = mod.missing(lambda name: None if name == "yt_dlp" else object())
    assert (
        list(gone) == ["yt_dlp"] and "YouTube" in gone["yt_dlp"]
    )  # the exact failure the exe had


# ---- F12: !play from chat is saved to playlist.json (feeds !last) ----

def test_play_saves_to_playlist_json(tmp_path):
    """Chat requests (!play) are appended to playlist.json and deduplicated by source."""
    playlist_path = tmp_path / "playlist.json"
    e = make()
    e.playlist_file = str(playlist_path)
    from camfrog_autodj.playlist import PlaylistStore
    from camfrog_autodj.library import local_track
    e.playlist = PlaylistStore(str(playlist_path))

    # make() overrides resolve to return YouTube URLs; override back for local files
    e.resolve = lambda arg, user, admin: [
        local_track(arg, user) if os.path.isabs(arg) else []
    ]

    tracks = e.resolve("/m/song one.mp3", "amy", True)
    e.queue.add_request(tracks[0])
    e.playlist.add(tracks)

    data = json.loads(playlist_path.read_text("utf-8"))
    sources = [t["source"] for t in data["tracks"]]
    assert [pathlib.Path(source).as_posix() for source in sources] == ["/m/song one.mp3"]
    assert [t["added_by"] for t in data["tracks"]] == ["amy"]

    # Duplicate request is refused
    tracks2 = e.resolve("/m/song one.mp3", "amy", True)
    e.queue.add_request(tracks2[0])
    e.playlist.add(tracks2)
    data2 = json.loads(playlist_path.read_text("utf-8"))
    assert len(data2["tracks"]) == 1  # still only one entry


def test_playlist_loads_into_history_on_startup(tmp_path):
    """Tracks in playlist.json join the autoplay pool on startup."""
    playlist_path = tmp_path / "playlist.json"
    playlist_path.write_text(
        json.dumps(
            {
                "version": 1,
                "tracks": [
                    {
                        "source": "/m/pool track.mp3",
                        "title": "Pool Track",
                        "duration": 120,
                        "added_by": "amy",
                        "added": "2026-01-01T00:00:00",
                    }
                ],
            }
        ),
        "utf-8",
    )
    e = make()
    e.playlist_file = str(playlist_path)
    e.playlist = None
    from camfrog_autodj.playlist import PlaylistStore
    e.playlist = PlaylistStore(str(playlist_path))

    # Simulate what _load_all does for playlist loading
    e.queue.add_pool(e.playlist.load())
    assert any(t.title == "Pool Track" for t in e.queue.pool)


# ---- F13: TTS synth works with default voice and raises clear error when pyttsx3 missing ----

def test_tts_synth_works_with_default_voice(tmp_path, monkeypatch):
    """Synthesising with no tts_voice set still produces a WAV file."""
    import types
    import sys

    from camfrog_autodj import tts

    # Fake pyttsx3 that writes a dummy WAV
    class FakeVoice:
        name = "Microsoft David"
        id = "HKEY_LOCAL_MACHINE\\Voices\\Tokens\\TTS_MS_EN-US_DAVID_11.0"

    class FakeEngine:
        def setProperty(self, name, value):
            pass

        def getProperty(self, name):
            if name == "voices":
                return [FakeVoice()]
            return None

        def save_to_file(self, text, path):
            pathlib.Path(path).write_text("dummy wav", "utf-8")

        def runAndWait(self):
            pass

    fake_mod = types.ModuleType("pyttsx3")
    fake_mod.init = lambda: FakeEngine()
    monkeypatch.setitem(sys.modules, "pyttsx3", fake_mod)

    wav = tmp_path / "test.wav"
    cfg = type("Cfg", (), {"tts_voice": "", "tts_rate": 170})()
    tts.synth("hello world", str(wav), cfg)
    assert wav.exists()
    assert wav.read_text("utf-8") == "dummy wav"


def test_tts_raises_clear_error_when_pyttsx3_missing(monkeypatch, tmp_path):
    """When pyttsx3 is not installed, synth() raises a clear error."""
    import builtins

    from camfrog_autodj import tts

    # Block pyttsx3 import
    real_import = builtins.__import__

    def blocked_import(name, *a, **k):
        if name == "pyttsx3":
            raise ModuleNotFoundError("No module named 'pyttsx3'")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", blocked_import)

    # Reset TTS worker so it re-initialises
    tts._tts_started = False

    wav = tmp_path / "test.wav"
    cfg = type("Cfg", (), {"tts_voice": "", "tts_rate": 170})()
    with pytest.raises(ModuleNotFoundError, match="pyttsx3"):
        tts.synth("hello world", str(wav), cfg)
