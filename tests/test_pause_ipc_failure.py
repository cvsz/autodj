"""Test that pause/resume only update state when IPC confirms success."""

import threading
from unittest.mock import MagicMock

from camfrog_autodj.config import Config
from camfrog_autodj.adapters import NullAdapter
from camfrog_autodj.engine import Engine


def test_pause_fails_when_ipc_unavailable():
    """Pause should not set paused=True when IPC fails."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)
    eng.player = MagicMock()
    eng.player.set_pause.return_value = False  # IPC failure
    eng.current = MagicMock()

    # Should not set paused=True when IPC fails
    eng.pause()
    assert eng.paused is False
    assert eng._paused_at is None


def test_resume_fails_when_ipc_unavailable():
    """Resume should not clear paused state when IPC fails."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)
    eng.player = MagicMock()
    eng.player.set_pause.return_value = False  # IPC failure
    eng.current = MagicMock()
    eng.paused = True
    eng._paused_at = 1000.0

    # Should not clear paused when IPC fails
    eng.resume()
    assert eng.paused is True
    assert eng._paused_at is not None


def test_pause_succeeds_when_ipc_available():
    """Pause should set paused=True when IPC succeeds."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)
    eng.player = MagicMock()
    eng.player.set_pause.return_value = True  # IPC success
    eng.current = MagicMock()

    eng.pause()
    assert eng.paused is True
    assert eng._paused_at is not None


def test_resume_succeeds_when_ipc_available():
    """Resume should clear paused state when IPC succeeds."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)
    eng.player = MagicMock()
    eng.player.set_pause.return_value = True  # IPC success
    eng.current = MagicMock()
    eng.paused = True
    eng._paused_at = 1000.0

    eng.resume()
    assert eng.paused is False
    assert eng._paused_at is None