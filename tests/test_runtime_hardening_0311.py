"""Runtime fixes found live on 2026-11-23."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import Mock

from autodj import __main__ as main_mod
from autodj.engine import Engine


def test_second_instance_with_the_same_config_is_refused(monkeypatch, tmp_path):
    names = set()

    def fake_mutex(name):
        existed = name in names
        names.add(name)
        return object(), existed

    monkeypatch.setattr(main_mod, "_create_mutex", fake_mutex)
    monkeypatch.setattr(main_mod, "_show_already_running", lambda: None)
    cfg = str(tmp_path / "config.toml")
    assert main_mod._single_instance(cfg) is True
    assert main_mod._single_instance(cfg) is False  # same install/config: refused
    assert main_mod._single_instance(str(tmp_path / "room2.toml")) is True  # another room: ok


def test_frozen_exe_without_arguments_opens_the_gui(monkeypatch):
    seen = {}
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "argv", ["zAutoDJ.exe"])
    monkeypatch.setattr("autodj.paths.prepare_comtypes", lambda: None)
    monkeypatch.setattr(main_mod, "_run", lambda a, level: seen.setdefault("gui", a.gui))
    main_mod.main()
    assert seen["gui"] is True


def test_cli_without_gui_flag_stays_headless(monkeypatch):
    seen = {}
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(sys, "argv", ["autodj"])
    monkeypatch.setattr("autodj.paths.prepare_comtypes", lambda: None)
    monkeypatch.setattr(main_mod, "_run", lambda a, level: seen.setdefault("gui", a.gui))
    main_mod.main()
    assert seen["gui"] is False


def _engine():
    e = Mock()
    e.cfg.bot_nick = "AutoDJ"
    e.blocked = set()
    e.admins = {"seaza", "zdevz"}
    e.cfg.admin_greeting_enabled = True
    e._own_nicks = set()
    e._is_own_account = lambda u: Engine._is_own_account(e, u)
    e.cfg.greeting_ignore = []
    e.cfg.mic_greeting_ignore = []
    e.cfg.greeting_ignore_regex = r"(?i)bot$"
    e._never_greet = lambda u: Engine._never_greet(e, u)
    return e


def test_echo_teaches_the_own_account_and_it_is_never_greeted():
    e = _engine()
    e._is_echo.return_value = True
    assert (
        Engine._should_ignore_message(e, SimpleNamespace(user="Seaza", text="now playing")) is True
    )
    assert e._own_nicks == {"seaza"}
    assert Engine._greet_user(e, "Seaza") is False  # was: "welcome back, admin Seaza"
    e._handle_admin_greeting.assert_not_called()
    Engine._greet_user(e, "zdevz")  # other admins are still greeted
    e._handle_admin_greeting.assert_called_once()


def test_non_echo_line_is_not_learned():
    e = _engine()
    e._is_echo.return_value = False
    assert Engine._should_ignore_message(e, SimpleNamespace(user="zdevz", text="!play x")) is False
    assert e._own_nicks == set()
