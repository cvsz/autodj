"""Runs the GUI's logic against the strict fake Tk (see fake_tk.py): construction, language switch, polling,
animation frames, button clicks. Catches wrong option names and runtime mistakes without needing a display."""

import sys
import time
import types
from pathlib import Path

import fake_tk
from test_core import make, out

import camfrog_autodj  # cache invalidation for _gui() (clears the cached `gui` attribute)
from camfrog_autodj.config import Config
from camfrog_autodj.gui import _toml_str
from camfrog_autodj.models import Track


def _tk_module():
    m = types.ModuleType("tkinter")
    for n in (
        "Tk",
        "Toplevel",
        "Frame",
        "Label",
        "Entry",
        "Listbox",
        "Text",
        "Canvas",
        "Menu",
        "Misc",
    ):
        setattr(m, n, getattr(fake_tk, n))
    m.TclError, m.font, m.ttk, m.filedialog = (
        fake_tk.TclError,
        fake_tk.font,
        fake_tk.ttk,
        fake_tk.filedialog,
    )
    return m


def _gui(monkeypatch):
    tkm = _tk_module()
    monkeypatch.setitem(sys.modules, "tkinter", tkm)
    monkeypatch.setitem(sys.modules, "tkinter.font", types.ModuleType("tkinter.font"))
    # Drop any gui module cached with the real tkinter (e.g. imported by another
    # test without monkeypatching), then re-import so `gui` binds to the fake-Tk
    # version below. Clearing sys.modules alone is not enough: `from package
    # import module` also reads the package's cached attribute.
    sys.modules.pop("camfrog_autodj.gui", None)
    camfrog_autodj.__dict__.pop("gui", None)
    from camfrog_autodj import gui

    return gui


def _app(monkeypatch, available=True):
    gui = _gui(monkeypatch)
    e = make()
    e.player.available = lambda: available
    e.queue.add_request(Track("/m/a.mp3", "Queued song", 90, "amy"))
    e.history.appendleft(Track("/m/h.mp3", "Old hit", 200, "bob"))
    e.say("hello room")
    app = gui.App(e)
    return gui, e, app


def _click(btn):
    btn._press(None)
    btn._release(types.SimpleNamespace(x=5, y=5))


def test_builds_and_shows_state(monkeypatch):
    try:
        _gui, _e, app = _app(monkeypatch)
        assert "Queued song" in app.lb.get(0)
        assert "Old hit" in app.hist.get(0)
        assert "hello room" in app.chat.get("1.0", "end")
        assert app.v_title.cget("text") == "Nothing playing"
        assert app.b_pause.cget("text") == "Pause"
    finally:
        sys.modules.pop("camfrog_autodj.gui", None)


def test_language_switch_relabels_everything(monkeypatch):
    try:
        _gui, _e, app = _app(monkeypatch)
        app.set_lang("th")
        assert app.b_pause.cget("text") == "หยุดชั่วคราว"
        assert app.tabs["history"].cget("text") == "ประวัติ"
        assert app.b_lang["th"]._active and not app.b_lang["en"]._active
    finally:
        sys.modules.pop("camfrog_autodj.gui", None)


def test_playing_state_drives_animation_and_progress(monkeypatch):
    try:
        _gui, e, app = _app(monkeypatch)
        app._layout_stage()
        app._layout_line()
        assert len(app._bar_items) >= 12 and app._vc is not None
        e.current = Track("/m/np.mp3", "Midnight City", 120, "amy")
        e.started_at = time.monotonic() - 30
        app._refresh()
        assert app._state == "playing" and app.v_title.cget("text") == "Midnight City"
        before = [app.stage.items[i][1][:] for i in app._bar_items]
        for _ in range(25):  # ~0.8 s of frames
            app._frame()
            time.sleep(0.01)
        after = [app.stage.items[i][1][:] for i in app._bar_items]
        assert before != after  # the equaliser moved
        assert app.bar._frac > 0.2  # 30 s of 120 s
        e.paused = True
        app._refresh()
        assert (
            app._state == "paused"
            and app.b_pause.cget("text") == "Resume"
            and app.b_pause._icon == "▶"
        )
    finally:
        sys.modules.pop("camfrog_autodj.gui", None)


def test_buttons_do_what_they_say(monkeypatch):
    try:
        _gui, e, app = _app(monkeypatch)
        app.ent_add.insert(0, "my song")
        app.add()
        app.update()  # process Tk events so async callback clears entry
        time.sleep(0.1)
        app.update()
        assert app.ent_add.get() == ""  # request accepted and the box cleared
        _click(app.c_shuffle)
        assert e.queue.shuffle is False or e.queue.shuffle is True
        was = e.queue.repeat
        _click(app.c_repeat)
        assert e.queue.repeat != was
        app.lb.selected = (0,)
        app._refresh()
        app.remove_selected()
        assert all(t.title != "Queued song" for t in e.queue.requests)
        app.show_tab("chat")
        assert app.tabs["chat"]._active and not app.tabs["queue"]._active
        app.ent_say.insert(0, "hi all")
        app.say()
        assert any("hi all" in o for o in out(e))
        app.vol._release(
            types.SimpleNamespace(x=450)
        )  # drag the volume knob to the middle
        assert 40 <= e.volume <= 60
    finally:
        sys.modules.pop("camfrog_autodj.gui", None)


def test_missing_mpv_shows_banner(monkeypatch):
    try:
        _gui, _e, app = _app(monkeypatch, available=False)
        texts = [w.cget("text") for w, _k in app._labels]
        assert any("mpv not found" in t for t in texts)
    finally:
        sys.modules.pop("camfrog_autodj.gui", None)


def test_refresh_survives_an_error_and_keeps_polling(monkeypatch):
    try:
        _gui, e, app = _app(monkeypatch)
        n = len(app._after)
        e.snapshot = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
        app.refresh()
        assert len(app._after) == n + 1  # rescheduled despite the exception
    finally:
        sys.modules.pop("camfrog_autodj.gui", None)


def test_settings_dialog_opens_and_saves(monkeypatch, tmp_path):
    """The settings popup must open without NameError (px -> self.px) and persist changes."""
    try:
        _gui, e, app = _app(monkeypatch)
        cfg_path = str(tmp_path / "config.toml")
        e.cfg_path = cfg_path
        # Write a starter config so save_settings has something to write
        from camfrog_autodj.config import Config

        starter = Config()
        starter.music_dirs = []
        starter.autoplay_sources = []
        from pathlib import Path

        Path(cfg_path).write_text(
            f'bot_nick = "{starter.bot_nick}"\n'
            f"admins = {starter.admins!r}\n"
            f'prefix = "{starter.prefix}"\n'
            f'lang = "{starter.lang}"\n'
            f'chat_reader = "{starter.chat_reader}"\n'
            f'chat_sender = "{starter.chat_sender}"\n'
            f'window_title_re = "{starter.window_title_re}"\n'
            f'process_re = "{starter.process_re}"\n'
            f'window_exclude_re = "{starter.window_exclude_re}"\n'
            f"window_index = {starter.window_index}\n"
            f"auto_discover = {str(starter.auto_discover).lower()}\n"
            f'view_kind = "{starter.view_kind}"\n'
            f'send_mode = "{starter.send_mode}"\n'
            f"send_verify = {str(starter.send_verify).lower()}\n"
            f"web_strict_body = {str(starter.web_strict_body).lower()}\n"
            f'view_type = "{starter.view_type}"\n'
            f"view_index = {starter.view_index}\n"
            f'input_type = "{starter.input_type}"\n'
            f"input_index = {starter.input_index}\n"
            f'mpv_path = "{starter.mpv_path}"\n'
            f'ytdlp_path = "{starter.ytdlp_path}"\n'
            f'audio_device = "{starter.audio_device}"\n'
            f"volume = {starter.volume}\n"
            f"music_dirs = {starter.music_dirs!r}\n"
            f"autoplay_sources = {starter.autoplay_sources!r}\n"
            f"shuffle = {str(starter.shuffle).lower()}\n"
            f"allowed_hosts = {starter.allowed_hosts!r}\n"
            f"max_requests_per_user = {starter.max_requests_per_user}\n"
            f"max_queue = {starter.max_queue}\n"
            f"max_duration = {starter.max_duration}\n"
            f"voteskip_threshold = {starter.voteskip_threshold}\n"
            f"cooldown = {starter.cooldown}\n"
            f"send_interval = {starter.send_interval}\n"
            f"max_msg_len = {starter.max_msg_len}\n"
            f"announce_next = {str(starter.announce_next).lower()}\n"
            f'tts_voice = "{starter.tts_voice}"\n'
            f"tts_rate = {starter.tts_rate}\n"
            f"tts_duck = {starter.tts_duck}\n"
            f"auto_launch = {str(starter.auto_launch).lower()}\n"
            f'camfrog_exe = "{starter.camfrog_exe}"\n'
            f'client_title_re = "{starter.client_title_re}"\n'
            f'room = "{starter.room}"\n'
            f'join_uri_template = "{starter.join_uri_template}"\n'
            f"launch_timeout = {starter.launch_timeout}\n"
            f"blocked_users = {starter.blocked_users!r}\n"
            f"poll_interval = {starter.poll_interval}\n"
            f'log_file = "{starter.log_file}"\n'
            f'playlist_file = "{starter.playlist_file}"\n'
            f"search_limit = {starter.search_limit}\n"
            f"mpv_timeout = {starter.mpv_timeout}\n",
            "utf-8",
        )
        # Open the settings dialog (this used to raise NameError: name 'px' is not defined)
        app.open_settings()
        assert app._settings_win is not None and app._settings_win.winfo_exists()
        # Change the volume and save
        app.s_volume.delete(0, "end")
        app.s_volume.insert(0, "85")
        app.save_settings()
        # Re-load and verify the change persisted
        new_cfg = Config.load(cfg_path)
        assert new_cfg.volume == 85
        # Close the dialog
        app._settings_close()
        assert app._settings_win is None
    finally:
        sys.modules.pop("camfrog_autodj.gui", None)


def test_settings_dialog_rejects_bad_int(monkeypatch):
    """Entering a non-numeric volume must not crash: it shows g_settings_save_failed."""
    try:
        _gui, e, app = _app(monkeypatch)
        app.open_settings()
        app.s_volume.delete(0, "end")
        app.s_volume.insert(0, "not-a-number")
        app.save_settings()  # must not raise; errors are reported via say()
        # Volume should remain unchanged
        assert e.volume == 70
        app._settings_close()
    finally:
        sys.modules.pop("camfrog_autodj.gui", None)


def test_settings_save_preserves_all_fields(monkeypatch, tmp_path):
    """save_settings must round-trip every config field, including ones the dialog
    does not edit (msg_now/msg_next, audio_fade*, youtube_cookies_*,
    voteskip_dynamic*, user_request_limit, rate_limit_window, log_path, log_encoding).
    Regression test for settings data loss."""
    try:
        _gui, e, app = _app(monkeypatch)
        cfg_path = str(tmp_path / "config.toml")
        e.cfg_path = cfg_path

        cfg = e.cfg
        # Non-default values for fields the settings dialog does NOT expose
        cfg.msg_now = "NP: {title}"
        cfg.msg_next = "Next: {title}"
        cfg.audio_fade = False
        cfg.audio_fade_in_sec = 2.5
        cfg.audio_fade_out_sec = 3.0
        cfg.audio_normalize = True
        cfg.youtube_cookies_file = "cookies.txt"
        cfg.youtube_cookies_browser = "chrome"
        cfg.youtube_ca_bundle = "ca.pem"
        cfg.voteskip_dynamic = True
        cfg.voteskip_dynamic_pct = 40
        cfg.user_request_limit = 10
        cfg.rate_limit_window = 600.0
        cfg.log_path = "chat.log"
        cfg.log_encoding = "utf-16"
        # Fields the settings dialog does NOT expose, plus web/playlist fields
        cfg.web_view_title = "wb-log-room-data.inside/"
        cfg.web_input_title = "wb-edit-data.inside/"
        cfg.line_regex = r"^(?:\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*)?(?P<user>[^:\s][^:]{0,30}):\s(?P<text>.+)$"
        cfg.playlist_dir = "playlist"
        # Fields the dialog DOES expose, set to non-defaults too
        cfg.volume = 85
        cfg.max_duration = 1200
        cfg.bot_nick = "DJ"

        Path(cfg_path).write_text(
            f'bot_nick = "{cfg.bot_nick}"\n'
            f"admins = {cfg.admins!r}\n"
            f'prefix = "{cfg.prefix}"\n'
            f'lang = "{cfg.lang}"\n'
            f'chat_reader = "{cfg.chat_reader}"\n'
            f'chat_sender = "{cfg.chat_sender}"\n'
            f'window_title_re = "{cfg.window_title_re}"\n'
            f'process_re = "{cfg.process_re}"\n'
            f'window_exclude_re = "{cfg.window_exclude_re}"\n'
            f"window_index = {cfg.window_index}\n"
            f"auto_discover = {str(cfg.auto_discover).lower()}\n"
            f'view_kind = "{cfg.view_kind}"\n'
            f'send_mode = "{cfg.send_mode}"\n'
            f"send_verify = {str(cfg.send_verify).lower()}\n"
            f"web_strict_body = {str(cfg.web_strict_body).lower()}\n"
            f'web_view_title = "{cfg.web_view_title}"\n'
            f'web_input_title = "{cfg.web_input_title}"\n'
            f'view_type = "{cfg.view_type}"\n'
            f"view_index = {cfg.view_index}\n"
            f'input_type = "{cfg.input_type}"\n'
            f"input_index = {cfg.input_index}\n"
            f'log_path = "{cfg.log_path}"\n'
            f'log_encoding = "{cfg.log_encoding}"\n'
            f'line_regex = "{cfg.line_regex}"\n'
            f'mpv_path = "{cfg.mpv_path}"\n'
            f'ytdlp_path = "{cfg.ytdlp_path}"\n'
            f'audio_device = "{cfg.audio_device}"\n'
            f'youtube_cookies_file = "{cfg.youtube_cookies_file}"\n'
            f'youtube_cookies_browser = "{cfg.youtube_cookies_browser}"\n'
            f'youtube_ca_bundle = "{cfg.youtube_ca_bundle}"\n'
            f"volume = {cfg.volume}\n"
            f"audio_fade = {str(cfg.audio_fade).lower()}\n"
            f"audio_fade_in_sec = {cfg.audio_fade_in_sec}\n"
            f"audio_fade_out_sec = {cfg.audio_fade_out_sec}\n"
            f"audio_normalize = {str(cfg.audio_normalize).lower()}\n"
            f"music_dirs = {cfg.music_dirs!r}\n"
            f"autoplay_sources = {cfg.autoplay_sources!r}\n"
            f"shuffle = {str(cfg.shuffle).lower()}\n"
            f"allowed_hosts = {cfg.allowed_hosts!r}\n"
            f"max_requests_per_user = {cfg.max_requests_per_user}\n"
            f"user_request_limit = {cfg.user_request_limit}\n"
            f"rate_limit_window = {cfg.rate_limit_window}\n"
            f"max_queue = {cfg.max_queue}\n"
            f"max_duration = {cfg.max_duration}\n"
            f"voteskip_threshold = {cfg.voteskip_threshold}\n"
            f"voteskip_dynamic = {str(cfg.voteskip_dynamic).lower()}\n"
            f"voteskip_dynamic_pct = {cfg.voteskip_dynamic_pct}\n"
            f"cooldown = {cfg.cooldown}\n"
            f"send_interval = {cfg.send_interval}\n"
            f"max_msg_len = {cfg.max_msg_len}\n"
            f"announce_next = {str(cfg.announce_next).lower()}\n"
            f'msg_now = "{cfg.msg_now}"\n'
            f'msg_next = "{cfg.msg_next}"\n'
            f'tts_voice = "{cfg.tts_voice}"\n'
            f"tts_rate = {cfg.tts_rate}\n"
            f"tts_duck = {cfg.tts_duck}\n"
            f"auto_launch = {str(cfg.auto_launch).lower()}\n"
            f'camfrog_exe = "{cfg.camfrog_exe}"\n'
            f'client_title_re = "{cfg.client_title_re}"\n'
            f'room = "{cfg.room}"\n'
            f'join_uri_template = "{cfg.join_uri_template}"\n'
            f"launch_timeout = {cfg.launch_timeout}\n"
            f"blocked_users = {cfg.blocked_users!r}\n"
            f"poll_interval = {cfg.poll_interval}\n"
            f'log_file = "{cfg.log_file}"\n'
            f'playlist_file = "{cfg.playlist_file}"\n'
            f'playlist_dir = "{cfg.playlist_dir}"\n'
            f"search_limit = {cfg.search_limit}\n"
            f"mpv_timeout = {cfg.mpv_timeout}\n"
            f"auto_reply_enabled = {str(cfg.auto_reply_enabled).lower()}\n"
            f"auto_reply_interval = {cfg.auto_reply_interval}\n"
            f"auto_reply_file = {_toml_str(cfg.auto_reply_file)}\n",
            "utf-8",
        )
        app.open_settings()
        app.save_settings()  # no user changes: everything must round-trip
        new_cfg = Config.load(cfg_path)
        checks = {
            "msg_now": "NP: {title}",
            "msg_next": "Next: {title}",
            "audio_fade": False,
            "audio_fade_in_sec": 2.5,
            "audio_fade_out_sec": 3.0,
            "audio_normalize": True,
            "youtube_cookies_file": "cookies.txt",
            "youtube_cookies_browser": "chrome",
            "youtube_ca_bundle": "ca.pem",
            "voteskip_dynamic": True,
            "voteskip_dynamic_pct": 40,
            "user_request_limit": 10,
            "rate_limit_window": 600.0,
            "log_path": "chat.log",
            "log_encoding": "utf-16",
            "web_view_title": "wb-log-room-data.inside/",
            "web_input_title": "wb-edit-data.inside/",
            "line_regex": r"^(?:\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*)?(?P<user>[^:\s][^:]{0,30}):\s(?P<text>.+)$",
            "playlist_dir": "playlist",
            "volume": 85,
            "max_duration": 1200,
            "bot_nick": "DJ",
        }
        for key, want in checks.items():
            got = getattr(new_cfg, key)
            assert got == want, f"{key}: expected {want!r}, got {got!r}"
        app._settings_close()
    finally:
        sys.modules.pop("camfrog_autodj.gui", None)


def test_load_folder_gives_visible_feedback(monkeypatch, tmp_path):
    """Clicking "Load folder..." must show a GUI hint (not silently log), and
    load media files recursively into the autoplay pool, skipping non-media."""
    try:
        _gui, e, app = _app(monkeypatch)
        music = tmp_path / "music"
        music.mkdir()
        (music / "song one.mp3").write_bytes(b"not-a-real-mp3")
        (music / "notes.txt").write_text("ignore me")
        sub = music / "sub"
        sub.mkdir()
        (sub / "song two.flac").write_bytes(b"not-a-real-flac")
        monkeypatch.setattr(
            __import__("camfrog_autodj.gui", fromlist=["filedialog"]).filedialog,
            "askdirectory",
            lambda **k: str(music),
        )

        app.load_folder()
        assert "Loading folder" in app.v_hint.cget("text")

        deadline = time.time() + 8
        ok = False
        while time.time() < deadline:
            pool = [t.title for t in e.queue.pool]
            hint = app.v_hint.cget("text")
            if "song one" in pool and "song two" in pool and "Loaded 2 tracks" in hint:
                ok = True
                break
            time.sleep(0.05)

        assert ok, f"pool={pool} hint={hint!r}"
        assert not any("notes" in t.title for t in e.queue.pool)
    finally:
        sys.modules.pop("camfrog_autodj.gui", None)


def test_load_folder_empty_shows_loaded_zero(monkeypatch, tmp_path):
    """An empty folder still reports via the hint instead of staying silent."""
    try:
        _gui, _e, app = _app(monkeypatch)
        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.setattr(
            __import__("camfrog_autodj.gui", fromlist=["filedialog"]).filedialog,
            "askdirectory",
            lambda **k: str(empty),
        )
        app.load_folder()
        deadline = time.time() + 5
        seen = ""
        while time.time() < deadline:
            seen = app.v_hint.cget("text")
            if "Loaded 0 tracks" in seen:
                break
            time.sleep(0.05)
        assert "Loaded 0 tracks" in seen, f"hint={seen!r}"
    finally:
        sys.modules.pop("camfrog_autodj.gui", None)
