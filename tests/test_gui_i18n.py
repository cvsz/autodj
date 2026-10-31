import pytest
from test_core import make, out

from camfrog_autodj import launcher
from camfrog_autodj.adapters.base import ChatMessage
from camfrog_autodj.config import Config
from camfrog_autodj.messages import STR
from camfrog_autodj.models import Track


def test_en_th_same_keys():
    assert STR["en"].keys() == STR["th"].keys()


def test_thai_replies_and_aliases():
    e = make()
    e.lang = "th"
    e.router.handle(ChatMessage("amy", "!เล่น เพลงหนึ่ง"))
    assert out(e) == ["เข้าคิวที่ 1: เพลงหนึ่ง [2:00] ขอโดย amy"]
    e.current = Track("s", "now", 90, "bob")
    e.router.handle(ChatMessage("amy", "!เพลงนี้"))
    e.router.handle(ChatMessage("amy", "!ถัดไป"))
    assert out(e) == [
        "กำลังเล่น: now [1:30] - ขอโดย bob",
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
    monkeypatch.setattr(
        launcher,
        "find_window",
        lambda pat, t: calls.append(("find", pat)) or state["up"],
    )
    monkeypatch.setattr(
        launcher,
        "_start",
        lambda exe: calls.append(("start", exe)) or state.update(up=True),
    )
    monkeypatch.setattr(launcher, "_open_uri", lambda u: calls.append(("uri", u)))
    launcher.ensure_room(cfg)
    assert ("start", "C:/cam.exe") in calls and ("uri", "cam://join/My%20Room") in calls
    assert [c[0] for c in calls].index("start") < [c[0] for c in calls].index("uri")


def test_launcher_requires_template(monkeypatch):
    monkeypatch.setattr(launcher, "find_window", lambda p, t: True)
    # Should log warning but not raise when join_uri_template is empty
    launcher.ensure_room(Config(room="x"))


def test_gui_smoke():
    tk = pytest.importorskip("tkinter")
    try:
        probe = tk.Tk()
        probe.destroy()
        del probe
    except tk.TclError:
        pytest.skip("no display")

    from camfrog_autodj.gui import App

    e = make()
    e.current = Track("s", "Midnight City", 243, "bob")
    e.started_at = __import__("time").monotonic() - 60
    e.queue.add_request(Track("q", "Queued song", 100, "amy"))
    e.say("hello")
    app = App(e)
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


def test_window_pick():
    from camfrog_autodj.windows import Cand, pick

    cs = [
        Cand(1, "Camfrog Video Chat", "A", 10),
        Cand(2, "My Room - Camfrog", "B", 10),
        Cand(3, "x Camfrog", "C", 99),
    ]
    assert pick(cs, self_pid=99).handle == 1
    assert pick(cs, prefer="my room", self_pid=99).handle == 2
    assert pick(cs, exclude_re="Video Chat$", self_pid=99).handle == 2
    assert pick(cs, index=5, self_pid=99).handle == 2
    assert pick([], self_pid=1) is None


def test_discover_pick_and_config(tmp_path):
    import re

    from camfrog_autodj.discover import (
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
    main = score_window(
        "Camfrog Video Chat", [Ctl("Edit", 0, "search", 0, 0, 200, 20)], rx
    )
    assert main is None
    ups = to_updates(best_room([f for f in (room, main) if f]))
    assert ups["view_type"] == "Document" and ups["view_index"] == 0
    assert ups["input_type"] == "Edit" and ups["input_index"] == 0
    p = tmp_path / "config.toml"
    p.write_text('bot_nick = "X"\nview_index = 3  # old\n# input_index = -1\n', "utf-8")
    assert save_config(str(p), ups)
    t = p.read_text("utf-8")
    assert (
        "view_index = 0  # old" in t
        and "input_index = 0" in t
        and 'bot_nick = "X"' in t
    )
    assert (tmp_path / "config.toml.bak").exists()
    assert not save_config(str(p), ups)
    from camfrog_autodj.config import Config as C

    assert re.fullmatch(C.load(str(p)).window_title_re, "My Room - Camfrog")


def test_window_pick_by_process():
    from camfrog_autodj.windows import Cand, pick

    cs = [
        Cand(
            1,
            "Camfrog AutoDJ - Claude - Google Chrome",
            "Chrome_WidgetWin_1",
            5,
            "chrome.exe",
        ),
        Cand(2, "My Room", "Qt", 6, "Camfrog Video Chat.exe"),
    ]
    assert pick(cs, exe_re="(?i)camfrog").handle == 2
    assert pick(cs, exe_re="(?i)zzz") is None
    assert pick(cs).handle == 1


def test_webchat_lines():
    import re

    from camfrog_autodj.adapters.base import parse_line
    from camfrog_autodj.webchat import tokens_to_lines

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
    assert (m.user, m.text) == ("zdevz", "!play")


def test_discover_web_updates():
    from camfrog_autodj.discover import Ctl, Found, to_updates

    ups = to_updates(Found("ZeaZDev: x", Ctl("Pane", 0), Ctl("Pane", 0), 3, web=True))
    assert ups["view_kind"] == "web" and "window_title_re" in ups
