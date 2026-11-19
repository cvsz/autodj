import time

import pytest
from test_core import make, out

from autodj import launcher
from autodj.adapters.base import ChatMessage
from autodj.config import Config
from autodj.messages import STR
from autodj.models import Track


def test_en_th_same_keys():
    assert STR["en"].keys() == STR["th"].keys()


def test_thai_replies_and_aliases():
    e = make()
    e._active_room_users.add("amy")
    e.lang = "th"
    e.router.handle(ChatMessage("amy", "เล่น เพลงหนึ่ง", is_im=True))
    assert out(e) == ["เข้าคิวที่ 1: เพลงหนึ่ง [2:00] ขอโดย amy"]
    e.current = Track("s", "now", 90, "bob")
    e.started_at = time.monotonic()
    e.router.handle(ChatMessage("amy", "!เพลงนี้"))
    e.router.handle(ChatMessage("amy", "!ถัดไป"))
    assert out(e) == [
        "กำลังเล่น: now [1:30] - ขอโดย bob (0:00/1:30)",
        "เพลงถัดไป: เพลงหนึ่ง [2:00] (amy)",
    ]
    e.router.handle(ChatMessage("amy", "!ข้าม"))
    assert "โหวตข้าม" in out(e)[0]
    e.router.handle(ChatMessage("amy", "!เสียง 5"))
    assert out(e) == ["amy: เฉพาะแอดมินเท่านั้น"]
    e.router.handle(ChatMessage("boss", "!สุ่ม on"))
    assert out(e) == ["สุ่มเพลง: เปิด"]


def test_custom_template_overrides_lang():
    e = make()
    e.cfg.msg_now = "NP {title}"
    assert e.fmt_now(Track("s", "x", 1, "u")) == "NP x"


def test_position_pause():
    e = make()
    e.current = Track("s", "x", 100, "u")
    e.started_at = 100.0
    e.player.set_pause = lambda v: True  # mock IPC accept
    import time

    real = time.monotonic
    time.monotonic = lambda: 110.0
    try:
        assert e.position() == 10.0
        e.pause()
        time.monotonic = lambda: 150.0
        assert e.position() == 10.0
        e.resume()
        time.monotonic = lambda: 155.0
        assert e.position() == 15.0
    finally:
        time.monotonic = real


def test_launcher_flow(monkeypatch):
    cfg = Config(
        auto_launch=True,
        camfrog_exe="C:/cam.exe",
        room="My Room",
        join_uri_template="cam://join/{room}",
    )
    calls = []
    state = {"up": False}

    def find_window(pat, t):
        calls.append(("find", pat))
        return state["up"]

    def _start(exe):
        calls.append(("start", exe))
        state.update(up=True)
        return None

    monkeypatch.setattr(launcher, "find_window", find_window)
    monkeypatch.setattr(launcher, "_start", _start)
    monkeypatch.setattr(launcher, "_open_uri", lambda u: calls.append(("uri", u)))
    launcher.ensure_room(cfg)
    assert ("start", "C:/cam.exe") in calls and ("uri", "cam://join/My%20Room") in calls
    assert [c[0] for c in calls].index("start") < [c[0] for c in calls].index("uri")


def test_launcher_requires_template(monkeypatch):
    monkeypatch.setattr(launcher, "find_window", lambda p, t: True)
    # Should log warning but not raise when join_uri_template is empty
    launcher.ensure_room(Config(room="x"))


def _make_app(app_cls, engine):
    """Create the real Tk App, skipping when the runner's Tcl install is unusable.

    Hosted Windows runners intermittently fail to read ``init.tcl`` when a second
    interpreter is created ("couldn't read file ... init.tcl: No error", or
    'invalid command name "tcl_findLibrary"'). That is an environment fault, not a
    GUI regression.
    """
    import tkinter as tk

    try:
        return app_cls(engine)
    except tk.TclError as exc:
        msg = str(exc)
        # Same runner fault, other spellings: missing tk.tcl / auto.tcl.
        if any(s in msg for s in ("init.tcl", "tcl_findLibrary", "tk.tcl", "auto.tcl")):
            pytest.skip(f"Tcl runtime unavailable on this runner: {exc}")
        raise


def test_gui_smoke():
    tk = pytest.importorskip("tkinter")
    try:
        probe = tk.Tk()
        probe.destroy()
        del probe
    except tk.TclError:
        pytest.skip("no display")

    from autodj.gui import App

    e = make()
    e.current = Track("s", "Midnight City", 243, "bob")
    e.started_at = __import__("time").monotonic() - 60
    e.queue.add_request(Track("q", "Queued song", 100, "amy"))
    e.say("hello")
    app = _make_app(App, e)
    try:
        app.update()
        assert app.v_title.cget("text") == "Midnight City"
        assert "Queued song" in app.lb.get(0)
        assert "hello" in app.chat.get("1.0", "end")
        app.set_lang("th")
        app.update()
        assert app.b_pause.cget("text") == "หยุดชั่วคราว"
    finally:
        app.close()
        del app
        # Release the Tcl interpreter on the same thread that created it.
        import gc

        gc.collect()


def test_settings_dialog_visible_saves_and_reopens(tmp_path):
    """Regression: the settings dialog rendered empty (entries hidden behind their
    row frames, labels without text), reported save results into the chat room,
    and could not be reopened after its window was destroyed."""
    tk = pytest.importorskip("tkinter")
    try:
        probe = tk.Tk()
        probe.destroy()
        del probe
    except tk.TclError:
        pytest.skip("no display")

    from autodj.gui import App

    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text('bot_nick = "AutoDJ"\n', encoding="utf-8")
    e = make()
    e.cfg_path = str(cfg_file)
    e.player.cfg = e.cfg
    app = _make_app(App, e)
    try:
        app.open_settings()
        app.update()
        app.geometry("900x900")
        app.update()
        win = app._settings_win
        assert win is not None and app._settings_visible
        assert app.s_mpv_path.winfo_viewable()  # entry not hidden behind its row frame
        assert any(
            isinstance(w, tk.Label) and w.cget("text") == e.t("g_settings_mpv_path")
            for w, _k in app._labels
        )
        app.s_default_track.delete(0, "end")
        app.s_default_track.insert(0, "https://www.youtube.com/watch?v=HhVVVgYsBYw")
        app.s_autoplay_idle_timeout.delete(0, "end")
        app.s_autoplay_idle_timeout.insert(0, "45")
        out(e)
        app.save_settings()
        app.update()
        saved = Config.load(str(cfg_file))
        assert saved.default_track.endswith("HhVVVgYsBYw")
        assert saved.autoplay_idle_timeout == 45.0
        assert e.cfg.autoplay_idle_timeout == 45.0  # applied to the running engine
        assert out(e) == []  # nothing posted into the room
        assert app._settings_status.cget("text")  # result shown in the dialog

        app.s_autoplay_idle_timeout.delete(0, "end")
        app.s_autoplay_idle_timeout.insert(0, "not-a-number")
        app.save_settings()
        assert e.cfg.autoplay_idle_timeout == 45.0  # invalid input leaves engine untouched

        win.destroy()  # destroyed by something other than the Close button
        app.update()
        app.set_lang("th")  # relabel must skip the dead widgets (and retitle the menu)
        app.open_settings()
        app.update()
        assert app._settings_win is not None and app._settings_win.winfo_exists()
        app.show_settings()  # menu toggle closes the panel and frees it
        app.update()
        assert app._settings_win is None and not app._settings_visible
    finally:
        app.close()
        win = None
        del app
        import gc

        gc.collect()


def test_window_pick():
    from autodj.windows import Cand, pick

    cs = [
        Cand(1, "Camfrog Video Chat", "A", 10),
        Cand(2, "My Room - Camfrog", "B", 10),
        Cand(3, "x Camfrog", "C", 99),
    ]
    picked = pick(cs, self_pid=99)
    assert picked is not None and picked.handle == 1
    picked = pick(cs, prefer="my room", self_pid=99)
    assert picked is not None and picked.handle == 2
    picked = pick(cs, exclude_re="Video Chat$", self_pid=99)
    assert picked is not None and picked.handle == 2
    picked = pick(cs, index=5, self_pid=99)
    assert picked is not None and picked.handle == 2
    assert pick([], self_pid=1) is None


def test_window_pick_prefers_main_client_over_room_list_dialog():
    from autodj.windows import Cand, pick

    cs = [
        Cand(1, "รายชื่อห้องสนทนา", "#32770", 10),  # room-list dialog
        Cand(2, "Camfrog Video Chat", "A", 10),
    ]
    picked = pick(cs, self_pid=99)
    assert picked is not None and picked.handle == 2


def test_discover_pick_and_config(tmp_path):
    import re

    from autodj.discover import (
        Ctl,
        best_room,
        save_config,
        score_window,
        to_updates,
    )

    rx = re.compile(Config().line_regex)
    chat = Ctl("Document", 0, "alice: hi\nbob: yo\n", 0, 0, 800, 500)
    box = Ctl("Edit", 0, "", 0, 520, 800, 550)
    nick = Ctl("Edit", 1, "me", 0, 10, 100, 30)
    room = score_window("My Room - Camfrog", [chat, nick, box], rx)
    main = score_window("Camfrog Video Chat", [Ctl("Edit", 0, "search", 0, 0, 200, 20)], rx)
    assert main is None
    best = best_room([f for f in (room, main) if f])
    assert best is not None
    ups = to_updates(best)
    assert ups["view_type"] == "Document" and ups["view_index"] == 0
    assert ups["input_type"] == "Edit" and ups["input_index"] == 0
    p = tmp_path / "config.toml"
    p.write_text('bot_nick = "X"\nview_index = 3  # old\n# input_index = -1\n', "utf-8")
    assert save_config(str(p), ups)
    t = p.read_text("utf-8")
    assert "view_index = 0  # old" in t and "input_index = 0" in t and 'bot_nick = "X"' in t
    assert (tmp_path / "config.toml.bak").exists()
    assert not save_config(str(p), ups)

    assert re.fullmatch(Config.load(str(p)).window_title_re, "My Room - Camfrog")


def test_window_pick_by_process():
    from autodj.windows import Cand, pick

    cs = [
        Cand(
            1,
            "CamfrogAutoDJ - Claude - Google Chrome",
            "Chrome_WidgetWin_1",
            5,
            "chrome.exe",
        ),
        Cand(2, "My Room", "Qt", 6, "Camfrog Video Chat.exe"),
    ]
    picked = pick(cs, exe_re="(?i)camfrog")
    assert picked is not None and picked.handle == 2
    assert pick(cs, exe_re="(?i)zzz") is None
    picked = pick(cs)
    assert picked is not None and picked.handle == 1


def test_webchat_lines():
    import re

    from autodj.adapters.base import parse_line
    from autodj.webchat import tokens_to_lines

    toks = [
        "date header",
        "ZeazBot",
        "4:02",
        "Hello, user Omegaria!",
        "ZeazBot",
        "4:10",
        "Hello,\xa0user",
        "zdevz",
        "5:43",
        "!play",
        "Zeasa",
        "5:44",
        "multi",
        "part",
        "ZeazBot",
        "5:45",
        "Success is not: easy",
        "cut-off-nick-less",
        "6:00",
    ]
    lines = tokens_to_lines(toks)
    assert lines[0] == "4:02 ZeazBot: Hello, user Omegaria!"
    assert "5:43 zdevz: !play" in lines and "5:44 Zeasa: multi part" in lines
    assert (
        lines[-1] == "5:45 ZeazBot: Success is not  easy"
        or lines[-1] == "5:45 ZeazBot: Success is not: easy"
    )
    assert len(lines) == 5  # the last message has no body yet: skipped
    rx = re.compile(Config().line_regex)
    m = parse_line("5:43 zdevz: !play", rx)
    assert m is not None
    assert (m.user, m.text) == ("zdevz", "!play")


def test_discover_web_updates():
    from autodj.discover import Ctl, Found, to_updates

    ups = to_updates(Found("ZeaZDev: x", Ctl("Pane", 0), Ctl("Pane", 0), 3, web=True))
    assert ups["view_kind"] == "web" and "window_title_re" in ups

