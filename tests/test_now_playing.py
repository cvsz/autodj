"""Now-playing announcements, "what song?" auto-answers and autoplay pool order."""

from __future__ import annotations

import time

from test_core import make, out

from autodj.adapters.base import ChatMessage
from autodj.models import Track
from autodj.playqueue import PlayQueue


def _pool(n: int) -> list[Track]:
    return [Track(f"s{i}", f"song {i}", 60, "AutoDJ") for i in range(n)]


def test_pop_pool_plays_the_announced_up_next_track():
    q = PlayQueue(shuffle=True)
    q.add_pool(_pool(10))
    for _ in range(30):
        promised = q.peek()  # what "Up next" announced
        assert q.pop_pool() is promised


def test_pool_loops_instead_of_draining():
    q = PlayQueue(shuffle=True)
    q.add_pool(_pool(3))
    played = [q.pop_pool() for _ in range(9)]
    assert all(t is not None for t in played)
    assert len(q.pool) == 3


def test_shuffle_bag_no_repeat_until_every_song_played():
    q = PlayQueue(shuffle=True)
    q.add_pool(_pool(6))
    first_pass = [q.pop_pool().source for _ in range(6)]
    assert sorted(first_pass) == sorted(f"s{i}" for i in range(6))


def test_np_question_in_room_gets_current_song():
    e = make()
    e.current = Track("s", "ลมหนาว", 200, "bob")
    e.started_at = time.monotonic()
    e.cfg.welcome_message_enabled = False  # only the answer is under test
    e._handle_room_message(ChatMessage("amy", "เพลงอะไรอะ เพราะดี"))
    msgs = out(e)
    assert len(msgs) == 1 and "ลมหนาว" in msgs[0] and "/3:20)" in msgs[0]


def test_np_question_cooldown_prevents_flood():
    e = make()
    e.current = Track("s", "x", 200, "bob")
    e.started_at = time.monotonic()
    e.cfg.welcome_message_enabled = False
    e._handle_room_message(ChatMessage("amy", "what song is this"))
    e._handle_room_message(ChatMessage("ben", "เพลงชื่ออะไรครับ"))
    assert len(out(e)) == 1


def test_np_question_can_be_disabled_and_ignores_commands():
    e = make()
    e.current = Track("s", "x", 200, "bob")
    e.cfg.np_question_reply = False
    e.cfg.welcome_message_enabled = False
    e._handle_room_message(ChatMessage("amy", "เพลงอะไร"))
    assert out(e) == []
    e.cfg.np_question_reply = True
    assert e._answer_np_question(ChatMessage("amy", "!play เพลงอะไรก็ได้")) is False


def test_next_template_eta_is_time_until_it_starts():
    e = make()
    e.cfg.msg_next = "next in {eta}: {title}"
    e.current = Track("s", "now", 180, "bob")
    e.started_at = time.monotonic() - 60  # 1:00 into a 3:00 song
    nxt = Track("n", "later", 100, "amy")
    assert e.fmt_next(nxt) == "next in 2:00: later"


def test_repeat_one_announces_only_once():
    e = make()
    t = Track("s", "loop", 1, "bob")
    calls = {"n": 0}

    def fake_play(*_a, **_k):
        calls["n"] += 1
        if calls["n"] >= 3:
            e.queue.repeat = "off"
        return True

    e.player.play = fake_play
    e.queue.repeat = "one"
    e._play_one_track(t, 0)
    now_lines = [m for m in out(e) if "loop" in m]
    assert calls["n"] == 3 and len(now_lines) == 1


def test_settings_writer_keeps_keys_missing_from_the_hand_list():
    from autodj.config import Config
    from autodj.gui import _append_remaining_keys

    cfg = Config()
    cfg.ai_api_key = "sk-test"
    cfg.auto_update_enabled = True
    lines = ['bot_nick = "AutoDJ"']
    _append_remaining_keys(lines, cfg)
    text = "\n".join(lines)
    assert 'ai_api_key = "sk-test"' in text
    assert "auto_update_enabled = true" in text
    assert text.count("bot_nick =") == 1
    import tomllib

    tomllib.loads(text)  # still valid TOML


# ---- Request rules: default song, FIFO queue, idle fallback ---------------------------

DEFAULT_URL = "https://www.youtube.com/watch?v=HhVVVgYsBYw"


def _engine_with_default():
    e = make()
    e.cfg.default_track = DEFAULT_URL
    e.cfg.autoplay_idle_timeout = 30.0
    e._remote = lambda src, user, playlist=False: [  # type: ignore[method-assign]
        Track(src, "Default Song", 3600, "someone")
    ]
    e.exec.submit = lambda fn, *a, **k: None  # type: ignore[method-assign]  # no delayed re-check
    e._active_room_users.update({"amy", "ben", "cat"})
    return e


def _req(e, user, song):
    e.router.handle(ChatMessage(user, f"play {song}", is_im=True))


def test_default_song_plays_at_startup():
    e = _engine_with_default()
    t = e._pop_next_track(time.monotonic())
    assert t is not None and t.source == DEFAULT_URL and t.title == "Default Song"
    assert t.requester == "AutoDJ" and not t.is_request


def test_first_request_cuts_the_default_song_immediately():
    e = _engine_with_default()
    e.current = e._pop_next_track(time.monotonic())  # default song playing
    _req(e, "amy", "song one")
    assert e.player.stopped == 1  # cut now
    assert [t.title for t in e.queue.requests] == ["song one"]


def test_second_request_queues_and_never_cuts_a_requested_song():
    e = _engine_with_default()
    e.current = e._pop_next_track(time.monotonic())
    _req(e, "amy", "song one")
    e.current = e._pop_next_track(time.monotonic())  # amy's song now playing
    assert e.current.title == "song one" and e.current.is_request
    stopped = e.player.stopped
    _req(e, "ben", "song two")
    _req(e, "cat", "song three")
    assert e.player.stopped == stopped  # amy's song keeps playing to the end
    assert [t.title for t in e.queue.requests] == ["song two", "song three"]  # FIFO


def test_queue_plays_in_arrival_order_before_any_default():
    e = _engine_with_default()
    for u, s in (("amy", "a"), ("ben", "b"), ("cat", "c")):
        _req(e, u, s)
    now = time.monotonic() + 999  # even long after the idle timeout
    order = [e._pop_next_track(now).title for _ in range(3)]
    assert order == ["a", "b", "c"]


def test_default_returns_only_after_queue_empty_and_30s_idle():
    e = _engine_with_default()
    _req(e, "amy", "a")
    e._pop_next_track(time.monotonic())  # amy's song taken from the queue
    t0 = e._last_user_request_time
    assert e._pop_next_track(t0 + 10) is None  # amy's song ended at +10: queue empty, wait
    assert e._pop_next_track(t0 + 31) is None  # only 21 s since the queue ran out
    t = e._pop_next_track(t0 + 41)
    assert t is not None and t.source == DEFAULT_URL  # 30 s empty + no request: default


def test_long_request_is_still_followed_by_a_full_idle_window():
    """A 4-minute request ends long after it was requested: still wait 30 s."""
    e = _engine_with_default()
    _req(e, "amy", "long song")
    t0 = e._last_user_request_time
    assert e._pop_next_track(t0).title == "long song"
    ended = t0 + 240
    assert e._pop_next_track(ended) is None  # used to start the default song right here
    assert e._pop_next_track(ended + 29) is None
    t = e._pop_next_track(ended + 30.5)  # not +30: float rounding of monotonic sums
    assert t is not None and t.source == DEFAULT_URL


def test_request_during_idle_window_cancels_the_default():
    e = _engine_with_default()
    _req(e, "amy", "a")
    t0 = e._last_user_request_time
    e._pop_next_track(t0)
    assert e._pop_next_track(t0 + 100) is None  # queue empty, window starts
    _req(e, "ben", "b")  # someone asks within the 30 s
    assert e._pop_next_track(time.monotonic()).title == "b"


def test_default_song_repeats_while_idle():
    e = _engine_with_default()
    now = time.monotonic()
    first = e._pop_next_track(now)
    second = e._pop_next_track(now + 4000)
    assert first.source == second.source == DEFAULT_URL and first is not second


def test_dead_default_link_falls_back_to_autoplay_pool():
    e = _engine_with_default()
    e.queue.add_pool([Track("p1", "pool song", 60, "AutoDJ")])
    t = e._pop_next_track(time.monotonic())
    e._track_failed(t, 1)
    nxt = e._pop_next_track(time.monotonic())
    assert nxt is not None and nxt.title == "pool song"


def test_without_default_track_pool_still_autoplays():
    e = make()
    e.cfg.default_track = ""
    e.queue.add_pool([Track("p1", "pool song", 60, "AutoDJ")])
    assert e._pop_next_track(time.monotonic()).title == "pool song"


# ---- Review findings (2026-11-18): regression tests ------------------------------------


def test_resolved_search_request_keeps_is_request_and_requester():
    e = make()
    t = Track("ytsearch1:some song", "some song", None, "amy")
    e.queue.add_request(t)
    e._remote = lambda *a, **k: [Track("https://youtu.be/x", "Some Song", 200, "AutoDJ")]  # type: ignore[method-assign]
    res = e._resolve_track_if_search(t)
    assert res.is_request and res.requester == "amy"


def test_local_default_track_is_played_directly(tmp_path):
    f = tmp_path / "intro.mp3"
    f.write_bytes(b"ID3")
    e = make()
    e.cfg.default_track = str(f)
    e._remote = lambda *a, **k: (_ for _ in ()).throw(AssertionError("no YouTube lookup"))  # type: ignore[method-assign]
    t = e._pop_next_track(time.monotonic())
    assert t is not None and t.source == str(f) and not t.is_request


def test_failed_default_lookup_is_not_retried_every_repeat():
    e = make()
    e.cfg.default_track = "https://www.youtube.com/watch?v=HhVVVgYsBYw"
    calls = []

    def boom(*a, **k):
        calls.append(1)
        raise RuntimeError("yt-dlp down")

    e._remote = boom  # type: ignore[method-assign]
    now = time.monotonic()
    for i in range(3):
        assert e._pop_next_track(now + i * 4000) is not None
    assert len(calls) == 1


def test_up_next_is_not_a_pool_track_when_default_song_follows():
    e = make()
    e.cfg.default_track = "https://www.youtube.com/watch?v=HhVVVgYsBYw"
    e.queue.add_pool([Track("p", "pool song", 60, "AutoDJ")])
    assert e._true_next() is None
    e.queue.add_request(Track("r", "req", 60, "amy"))
    assert e._true_next().title == "req"


def test_rate_limit_covers_every_play_alias():
    e = make()
    e.cfg.user_request_limit = 2
    e.cfg.max_requests_per_user = 50
    e._active_room_users.add("amy")
    for i, cmd in enumerate(["play", "aplay", "addm", "ขอเพลง", "เล่นเพลง", "เปิดเพลง"]):
        e.router.handle(ChatMessage("amy", f"{cmd} s{i}", is_im=True))
    assert len(e.queue.requests) == 2


def test_allow_play_in_room_false_means_im_only():
    e = make()
    e.cfg.allow_play_in_room = False
    e.router.handle(ChatMessage("amy", "!play abc"))
    assert not e.queue.requests
    assert e.t("im_only_command") in out(e)[0]
    e._active_room_users.add("amy")
    e.router.handle(ChatMessage("amy", "play abc", is_im=True))
    assert len(e.queue.requests) == 1


def test_im_require_room_presence():
    e = make()
    e.cfg.im_require_room_presence = True
    e.router.handle(ChatMessage("stranger", "play abc", is_im=True))
    assert not e.queue.requests
    e.cfg.im_require_room_presence = False
    e.router.handle(ChatMessage("stranger", "play abc", is_im=True))
    assert len(e.queue.requests) == 1


def test_im_command_with_prefix_works():
    e = make()
    e._active_room_users.add("amy")
    e.current = Track("s", "x", 60, "bob")
    e.started_at = time.monotonic()
    e.router.handle(ChatMessage("amy", "!np", is_im=True))
    lines = out(e)
    assert lines and "x" in lines[0]


def test_hbdp_respects_queue_limits_for_non_admins():
    e = make()
    e.cfg.max_queue = 1
    e._active_room_users.add("amy")
    e.router.handle(ChatMessage("amy", "hbdp Ann", is_im=True))
    e.router.handle(ChatMessage("amy", "hbdp Bob", is_im=True))
    assert len(e.queue.requests) <= 1


def test_cooldown_survives_cleanup_when_longer_than_window():
    e = make()
    e.cfg.cooldown = 600.0
    e.cfg.rate_limit_window = 60.0
    now = time.monotonic()
    e.router.last["amy"] = now - 120
    e.router.cleanup_expired_entries(now)
    assert "amy" in e.router.last


def test_favorites_concurrent_stores_do_not_lose_entries(tmp_path):
    from autodj.favorites import FavoritesStore

    cfgp = str(tmp_path / "config.toml")
    a, b = FavoritesStore(cfgp), FavoritesStore(cfgp)  # created before either saves
    a.add("amy", Track("s1", "t1", 60, "amy"))
    b.add("amy", Track("s2", "t2", 60, "amy"))
    assert [x["title"] for x in FavoritesStore(cfgp).list_for("amy")] == ["t1", "t2"]


def test_punishbot_cannot_target_admin():
    e = make()
    e.cfg.admin_punish_bot = True
    e.router.handle(ChatMessage("Boss", "!punishbot boss"))
    assert "/punish boss" not in out(e)


def test_welcome_cooldown_independent_of_machine_uptime(monkeypatch):
    import autodj.engine as eng

    e = make()
    e.cfg.room = "ZeaZDev"
    monkeypatch.setattr(eng.time, "monotonic", lambda: 5.0)  # PC booted 5 s ago
    e._handle_welcome_message(ChatMessage("amy", "hi"))
    expected = e.cfg.welcome_message_message.replace("{user}", "amy").replace("{room}", "ZeaZDev")
    assert out(e) == [expected]


def test_unknown_command_reaches_plugins(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # the stats plugin keeps plugin_stats.json in the CWD
    e = make()
    from autodj.plugins.manager import PluginManager

    e._plugin_manager = PluginManager(e, ["builtin.stats"])
    e._plugin_manager.load_plugins()
    e.router.handle(ChatMessage("amy", "!stats"))
    assert any("Total plays" in m for m in out(e))


def test_tts_play_file_ducks_and_restores_music(monkeypatch):
    import threading

    from autodj.config import Config
    from autodj.player import MpvPlayer

    p = MpvPlayer(Config(), threading.Event())
    vols: list[int] = []
    monkeypatch.setattr(p, "set_volume", lambda v: vols.append(v) or True)

    class FakeClip:  # never start a real mpv in tests (CI has none)
        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr("autodj.player.subprocess.Popen", lambda *a, **k: FakeClip())
    monkeypatch.setattr("autodj.player.kill_with_parent", lambda proc: True)
    p.play_file("tts.wav", duck_volume=20, restore_volume=70)
    assert vols == [20, 70]


def test_player_never_starts_mpv_after_shutdown(monkeypatch):
    import threading

    from autodj.config import Config
    from autodj.player import MpvPlayer

    stop = threading.Event()
    stop.set()
    p = MpvPlayer(Config(), stop)

    def no_popen(*a, **k):
        raise AssertionError("mpv started during shutdown")

    monkeypatch.setattr("autodj.player.subprocess.Popen", no_popen)
    assert p.play("https://youtu.be/x", 50, 10.0) is True


def test_end_to_end_request_flow_on_the_real_player_thread():
    """Default song -> 1st request cuts it -> 2nd request waits -> idle -> default again.

    Runs Engine._player_loop in its own thread with a player that really blocks for
    the (scaled-down) track length, so timing and cut/queue rules are exercised
    exactly as at runtime.
    """
    import threading

    e = make()
    e.cfg.default_track = DEFAULT_URL
    e.cfg.autoplay_idle_timeout = 1.0
    e.cfg.welcome_message_enabled = False
    e._active_room_users.update({"amy", "ben"})
    e._remote = lambda src, user, playlist=False, **k: [  # type: ignore[method-assign]
        Track(src, "Default Song", 30, "x")
    ]
    lengths = {"A": 0.8, "B": 0.4}
    e.resolve = lambda arg, user, admin: [  # type: ignore[method-assign]
        Track(f"https://youtu.be/{arg}", arg, lengths[arg], user)
    ]

    log: list[tuple[str, float, str]] = []  # (title, played seconds, how it ended)
    starts: list[str] = []  # titles in the order playback started

    class BlockingPlayer:
        skipped = False

        def __init__(self):
            self._stop = threading.Event()

        def available(self):
            return True

        def play(self, source, volume, duration=None):
            self._stop.clear()
            self.skipped = False
            starts.append(e.current.title if e.current else source)
            t0 = time.monotonic()
            cut = self._stop.wait(duration or 30)
            title = e.current.title if e.current else source
            log.append((title, time.monotonic() - t0, "cut" if cut else "end"))
            self.skipped = cut
            return True

        def stop(self):
            self._stop.set()

        def get_time_pos(self):
            return None

        def set_volume(self, v):
            return True

        def set_pause(self, v):
            return True

    e.player = BlockingPlayer()
    th = threading.Thread(target=e._player_loop, daemon=True)
    th.start()
    try:
        deadline = time.monotonic() + 5
        while not (e.current and e.current.source == DEFAULT_URL) and time.monotonic() < deadline:
            time.sleep(0.02)
        assert e.current and e.current.source == DEFAULT_URL  # default song at startup

        e.router.handle(ChatMessage("amy", "play A", is_im=True))  # cuts the default song
        time.sleep(0.15)
        e.router.handle(ChatMessage("ben", "play B", is_im=True))  # must wait for A

        deadline = time.monotonic() + 8
        while len(starts) < 4 and time.monotonic() < deadline:
            time.sleep(0.02)
    finally:
        e.stop_evt.set()
        e.wake.set()
        e.player.stop()
        th.join(3)

    assert starts[:4] == ["Default Song", "A", "B", "Default Song"], starts
    titles = [t for t, _, _ in log]
    assert titles[:3] == ["Default Song", "A", "B"], log
    assert log[0][2] == "cut"  # first request cut the default song immediately
    assert log[1][2] == "end" and log[1][1] >= 0.75  # A was NOT cut by ben's request
    assert log[2][2] == "end"  # B played to its end
    # (starts[3]) after the queue emptied and >= 1 s without requests, default returned
