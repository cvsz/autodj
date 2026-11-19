"""Regression: the first IM must not deadlock the chat loop (found in a live Camfrog test)."""

from __future__ import annotations

import threading

from camfrog_autodj.adapters import NullAdapter
from camfrog_autodj.adapters.base import ChatMessage
from camfrog_autodj.config import Config
from camfrog_autodj.engine import Engine


def _engine() -> Engine:
    cfg = Config()
    cfg.im_auto_reply_enabled = True
    cfg.im_auto_reply_message = "I'm a bot"
    cfg.im_auto_reply_cooldown = 60.0
    return Engine(cfg, NullAdapter())


def _run_with_timeout(fn, timeout: float = 3.0) -> bool:
    th = threading.Thread(target=fn, daemon=True)
    th.start()
    th.join(timeout)
    return not th.is_alive()


def test_im_auto_reply_does_not_deadlock():
    e = _engine()
    msg = ChatMessage("zdevz", "hello bot", is_im=True)
    assert _run_with_timeout(lambda: e._handle_im_message(msg)), "chat loop deadlocked"
    # The GUI poller must still get the lock afterwards.
    assert _run_with_timeout(e.chat_snapshot), "chat_snapshot blocked"
    _seq, _ver, log_entries = e.chat_snapshot()
    assert any("IM auto-reply to zdevz" in text for _who, text in log_entries)


def test_im_auto_reply_respects_cooldown():
    e = _engine()
    msg = ChatMessage("zdevz", "hello bot", is_im=True)
    for _ in range(2):  # timeout-guarded: a regression must fail, not hang the suite
        assert _run_with_timeout(lambda: e._handle_im_message(msg)), "chat loop deadlocked"
    _seq, _ver, log_entries = e.chat_snapshot()
    assert sum("IM auto-reply to zdevz" in text for _who, text in log_entries) == 1
