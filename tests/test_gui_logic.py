"""Runs the GUI's logic against the strict fake Tk (see fake_tk.py): construction, language switch, polling,
animation frames, button clicks. Catches wrong option names and runtime mistakes without needing a display."""
import sys
import time
import types

import pytest

import fake_tk
from test_core import make, out
from camfrog_autodj.models import Track


def _tk_module():
    m = types.ModuleType("tkinter")
    for n in ("Tk", "Frame", "Label", "Entry", "Listbox", "Text", "Canvas", "Menu", "Misc"):
        setattr(m, n, getattr(fake_tk, n))
    m.TclError, m.font, m.ttk, m.filedialog = fake_tk.TclError, fake_tk.font, fake_tk.ttk, fake_tk.filedialog
    return m


def _gui(monkeypatch):
    tkm = _tk_module()
    monkeypatch.setitem(sys.modules, "tkinter", tkm)
    monkeypatch.setitem(sys.modules, "tkinter.font", types.ModuleType("tkinter.font"))
    sys.modules.pop("camfrog_autodj.gui", None)
    import camfrog_autodj.gui as gui
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
        gui, e, app = _app(monkeypatch)
        app.refresh.__func__  # exists
        assert "Queued song" in app.lb.get(0)
        assert "Old hit" in app.hist.get(0)
        assert "hello room" in app.chat.get("1.0", "end")
        assert app.v_title.cget("text") == "Nothing playing"
        assert app.b_pause.cget("text") == "Pause"
    finally:
        sys.modules.pop("camfrog_autodj.gui", None)


def test_language_switch_relabels_everything(monkeypatch):
    try:
        gui, e, app = _app(monkeypatch)
        app.set_lang("th")
        assert app.b_pause.cget("text") == "หยุดชั่วคราว"
        assert app.tabs["history"].cget("text") == "ประวัติ"
        assert app.b_lang["th"]._active and not app.b_lang["en"]._active
    finally:
        sys.modules.pop("camfrog_autodj.gui", None)


def test_playing_state_drives_animation_and_progress(monkeypatch):
    try:
        gui, e, app = _app(monkeypatch)
        app._layout_stage()
        app._layout_line()
        assert len(app._bar_items) >= 12 and app._vc is not None
        e.current = Track("/m/np.mp3", "Midnight City", 120, "amy")
        e.started_at = time.monotonic() - 30
        app._refresh()
        assert app._state == "playing" and app.v_title.cget("text") == "Midnight City"
        before = [app.stage.items[i][1][:] for i in app._bar_items]
        for _ in range(25):                      # ~0.8 s of frames
            app._frame()
            time.sleep(0.01)
        after = [app.stage.items[i][1][:] for i in app._bar_items]
        assert before != after                    # the equaliser moved
        assert app.bar._frac > 0.2                # 30 s of 120 s
        e.paused = True
        app._refresh()
        assert app._state == "paused" and app.b_pause.cget("text") == "Resume" and app.b_pause._icon == "▶"
    finally:
        sys.modules.pop("camfrog_autodj.gui", None)


def test_buttons_do_what_they_say(monkeypatch):
    try:
        gui, e, app = _app(monkeypatch)
        app.ent_add.insert(0, "my song")
        app.add()
        time.sleep(0.2)
        assert app.ent_add.get() == ""                       # request accepted and the box cleared
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
        app.vol._release(types.SimpleNamespace(x=450))       # drag the volume knob to the middle
        assert 40 <= e.volume <= 60
    finally:
        sys.modules.pop("camfrog_autodj.gui", None)


def test_missing_mpv_shows_banner(monkeypatch):
    try:
        gui, e, app = _app(monkeypatch, available=False)
        texts = [w.cget("text") for w, _k in app._labels]
        assert any("mpv not found" in t for t in texts)
    finally:
        sys.modules.pop("camfrog_autodj.gui", None)


def test_refresh_survives_an_error_and_keeps_polling(monkeypatch):
    try:
        gui, e, app = _app(monkeypatch)
        n = len(app._after)
        e.snapshot = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
        app.refresh()
        assert len(app._after) == n + 1                        # rescheduled despite the exception
    finally:
        sys.modules.pop("camfrog_autodj.gui", None)
