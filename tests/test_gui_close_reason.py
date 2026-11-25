"""Closing the AutoDJ window logs what closed it, then stops the bot.

The bot was found stopped twice with only the normal shutdown lines in the log, so the
WM_DELETE_WINDOW handler now records whether a person (recent keyboard/mouse input) or
another program / the session end closed it.
"""

import logging
import types

import pytest

pytest.importorskip("tkinter")

import autodj.adapters.uia as uia  # noqa: E402
from autodj import gui  # noqa: E402


def _close_with_idle(monkeypatch, caplog, idle: float) -> tuple[str, list[bool]]:
    closed: list[bool] = []
    stub = types.SimpleNamespace(
        _USER_CLOSE_INPUT_S=gui.App._USER_CLOSE_INPUT_S, close=lambda: closed.append(True)
    )
    monkeypatch.setattr(uia, "_idle_seconds", lambda: idle)
    with caplog.at_level(logging.WARNING, logger="autodj"):
        gui.App._on_window_close(stub)
    return caplog.text, closed


def test_recent_input_is_reported_as_a_user_action(monkeypatch, caplog):
    text, closed = _close_with_idle(monkeypatch, caplog, 0.4)
    assert "AutoDJ window closed: user action (keyboard/mouse input 0.4 s before)" in text
    assert closed == [True]


def test_no_recent_input_points_at_another_program(monkeypatch, caplog):
    text, closed = _close_with_idle(monkeypatch, caplog, 900.0)
    assert "no keyboard/mouse input for 900 s: another program" in text
    assert closed == [True]


def test_unknown_idle_time_still_closes(monkeypatch, caplog):
    text, closed = _close_with_idle(monkeypatch, caplog, float("inf"))
    assert "user input time unknown" in text
    assert closed == [True]


def test_window_close_protocol_uses_the_logging_handler():
    import inspect

    src = inspect.getsource(gui.App.__init__)
    assert 'self.protocol("WM_DELETE_WINDOW", self._on_window_close)' in src
