"""Test that admin kick/ban/punish/delete commands work."""

from camfrog_autodj.adapters import NullAdapter
from camfrog_autodj.config import Config
from camfrog_autodj.engine import Engine


def test_kick_user_queues_command():
    """kick_user should queue /kick command."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)

    eng.kick_user("target")
    # Check outbox has the command
    assert not eng.outbox.empty()
    cmd = eng.outbox.get_nowait()
    assert cmd == "/kick target"


def test_ban_user_queues_command():
    """ban_user should queue /ban command."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)

    eng.ban_user("target")
    assert not eng.outbox.empty()
    cmd = eng.outbox.get_nowait()
    assert cmd == "/ban target"


def test_unban_user_queues_command():
    """unban_user should queue /unban command."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)

    eng.unban_user("target")
    assert not eng.outbox.empty()
    cmd = eng.outbox.get_nowait()
    assert cmd == "/unban target"


def test_punish_user_queues_command():
    """punish_user should queue /punish command."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)

    eng.punish_user("target")
    assert not eng.outbox.empty()
    cmd = eng.outbox.get_nowait()
    assert cmd == "/punish target"


def test_punish_bot_queues_command():
    """punish_bot should queue /punish command."""
    cfg = Config()
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)

    eng.punish_bot("target")
    assert not eng.outbox.empty()
    cmd = eng.outbox.get_nowait()
    assert cmd == "/punish target"


def test_delete_message_queues_command_when_enabled():
    """delete_message should queue /delete command when enabled."""
    cfg = Config()
    cfg.admin_delete_message_enabled = True
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)

    result = eng.delete_message("msg123")
    assert result is True
    assert not eng.outbox.empty()
    cmd = eng.outbox.get_nowait()
    assert cmd == "/delete msg123"


def test_delete_message_returns_false_when_disabled():
    """delete_message should return False when disabled."""
    cfg = Config()
    cfg.admin_delete_message_enabled = False
    adapter = NullAdapter()
    eng = Engine(cfg, adapter)

    result = eng.delete_message("msg123")
    assert result is False
    assert eng.outbox.empty()
