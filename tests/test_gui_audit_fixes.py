"""Regression tests for the gui.py audit fixes (threading, queue position, discover)."""

from __future__ import annotations

import sys
import threading
import types

from test_gui_logic import _app

from autodj.models import Track


def _cleanup():
    sys.modules.pop("autodj.gui", None)


def test_queued_hint_reports_real_position(monkeypatch):
    try:
        _gui, e, app = _app(monkeypatch)  # one request ("Queued song") is already queued
        t = Track("/m/b.mp3", "Second song", 60, "you")
        e.queue.add_request(t)
        assert app._queued_text([t]) == e.t(
            "queued_one", pos=2, title="Second song", dur=t.dur, user="you"
        )
    finally:
        _cleanup()


def test_ui_drops_callbacks_after_close(monkeypatch):
    try:
        _gui, _e, app = _app(monkeypatch)
        ran = []
        app._closing = True
        app._ui(ran.append, 1)
        assert ran == []
    finally:
        _cleanup()


def test_add_files_reenables_button_after_concurrent_callbacks(monkeypatch):
    try:
        gui, e, app = _app(monkeypatch)
        files = [f"/m/f{i}.mp3" for i in range(8)]
        monkeypatch.setattr(gui.filedialog, "askopenfilenames", lambda **_k: files, raising=False)
        threads = []
        lock = threading.Lock()  # fake Tk is not thread-safe; real Tk marshals after()

        def fake_request(src, on_success=None, on_error=None):
            def run():
                with lock:
                    on_success([Track(src, src, 1, "you")])

            th = threading.Thread(target=run)
            threads.append(th)
            th.start()

        monkeypatch.setattr(e, "request", fake_request)
        app.add_files()
        for th in threads:
            th.join()
        assert app.b_add._enabled is True  # PillButton keeps state itself
    finally:
        _cleanup()


def test_double_click_keeps_duplicate_title_track(monkeypatch):
    try:
        _gui, e, app = _app(monkeypatch)
        dup = Track("/m/a2.mp3", "Queued song", 90, "amy")  # same title + requester
        e.queue.add_request(dup, dedupe=False)
        app._refresh()
        monkeypatch.setattr(app.lb, "curselection", lambda: (1,))
        said = []
        monkeypatch.setattr(e, "say", lambda text, *a, **k: said.append(text))
        app._on_queue_double_click(None)
        assert e.queue.requests[0] is dup and len(e.queue.requests) == 2
        assert said and "amy" in said[-1] and "you" not in said[-1]
    finally:
        _cleanup()


def test_skip_and_prev_run_off_the_tk_thread(monkeypatch):
    try:
        _gui, e, app = _app(monkeypatch)
        seen: list[str] = []
        done = threading.Event()

        def fake_skip():
            seen.append(threading.current_thread().name)
            done.set()

        monkeypatch.setattr(e, "skip", fake_skip)
        app._skip_async()
        assert done.wait(5)
        assert seen == ["autodj-gui-ctl"]
    finally:
        _cleanup()


def test_discover_uses_exe_directly_when_frozen(monkeypatch):
    try:
        gui, e, app = _app(monkeypatch)
        shown = threading.Event()
        msgs: list[str] = []
        mb = types.ModuleType("tkinter.messagebox")
        mb.showinfo = lambda title, text: (msgs.append(text), shown.set())  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "tkinter.messagebox", mb)
        monkeypatch.setattr(sys.modules["tkinter"], "messagebox", mb, raising=False)
        calls = []

        def fake_run(argv, **_k):
            calls.append(argv)
            return types.SimpleNamespace(returncode=0, stdout="{'room': 'x'}\n", stderr="")

        import subprocess

        monkeypatch.setattr(subprocess, "run", fake_run)
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        app.do_discover()
        assert shown.wait(5)
        assert calls[0][0] == sys.executable and "-m" not in calls[0]
        assert calls[0][1:3] == ["--discover", "-c"]
        assert "Saved to" in msgs[0]
    finally:
        _cleanup()


def test_cli_discover_without_uia_does_not_start_the_bot(capsys):
    from autodj.__main__ import _auto_discover

    a = types.SimpleNamespace(discover=True, no_discover=False, config="config.toml")
    cfg = types.SimpleNamespace(chat_reader="console", chat_sender="console", auto_discover=False)
    assert _auto_discover(a, cfg) is True  # True = "handled, exit"
    assert "needs chat_reader" in capsys.readouterr().out
