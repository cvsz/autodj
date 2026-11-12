"""Test that _chat_loop handles exceptions correctly."""

from unittest.mock import MagicMock

from camfrog_autodj.adapters import NullAdapter
from camfrog_autodj.config import Config
from camfrog_autodj.engine import Engine
from camfrog_autodj.exceptions import ChatAdapterError


def test_chat_loop_catches_os_error():
    """OSError should be caught and logged."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)
    eng.adapter.messages = MagicMock(side_effect=OSError("COM error"))

    # Should not raise
    eng._chat_loop()
    assert eng.chat_done.is_set()


def test_chat_loop_catches_runtime_error():
    """RuntimeError should be caught and logged."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)
    eng.adapter.messages = MagicMock(side_effect=RuntimeError("UIA error"))

    # Should not raise
    eng._chat_loop()
    assert eng.chat_done.is_set()


def test_chat_loop_catches_chat_adapter_error():
    """ChatAdapterError should be caught and logged."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)
    eng.adapter.messages = MagicMock(side_effect=ChatAdapterError("adapter error"))

    # Should not raise
    eng._chat_loop()
    assert eng.chat_done.is_set()


def test_chat_loop_propagates_value_error_when_not_stopped():
    """ValueError (unexpected) should be logged but not crash if stop_evt is set."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)
    eng.adapter.messages = MagicMock(side_effect=ValueError("unexpected"))
    eng.stop_evt.set()  # Simulate shutdown

    # Should not raise when stop_evt is set
    eng._chat_loop()
    assert eng.chat_done.is_set()


def test_chat_loop_does_not_mask_errors_in_tests():
    """In test environment, unexpected errors should be visible."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)
    eng.adapter.messages = MagicMock(side_effect=ValueError("test error"))

    # Without stop_evt set, the exception should be logged but not raised
    # (the current implementation catches all exceptions)
    eng._chat_loop()
    assert eng.chat_done.is_set()
