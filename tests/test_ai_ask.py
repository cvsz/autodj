"""The AI answers only `!ai ask <question>`.

Live 2026-11-23: with an API key the bot would have sent every non-command room
line to the AI and posted the answer, including ZeazBot's quotes (one every few
minutes) and its own echoed lines.  The operator chose: no automatic replies,
everyone may ask with `!ai ask` / `!เอไอ ถาม`, settings stay admin-only, and
`!ai on` / status say plainly when no API key is configured.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from autodj import commands
from autodj.ai import AIClient
from autodj.commands import UserError
from autodj.config import Config
from autodj.engine import Engine


def _engine(key: str = "nvapi-test", enabled: bool = True):
    e = Mock()
    e.cfg = Config(ai_api_key=key, ai_enabled=enabled)
    e.ai = AIClient(e.cfg)
    e.t.side_effect = lambda k, **kw: k if not kw else f"{k}:{sorted(kw.items())}"
    e.refresh_ai.side_effect = lambda: setattr(e, "ai", AIClient(e.cfg))
    return e


def _msg(user="zdevz"):
    return SimpleNamespace(user=user, text="", is_im=False, local=False)


def test_room_chat_is_never_sent_to_the_ai():
    fake = Mock()
    fake.admins = set()
    fake._check_chat_rate_limit.return_value = True
    fake._answer_np_question.return_value = False
    fake.cfg.prefix = "!"
    Engine._handle_room_message(
        fake, SimpleNamespace(user="ZeazBot", text="Life is full of moments")
    )
    fake.ai_ask.assert_not_called()
    fake.ai.chat.assert_not_called()
    fake._ai_exec.submit.assert_not_called()
    assert not hasattr(Engine, "_ai_handle_room")


@pytest.mark.parametrize("arg", ["ask what is bpm", "ASK what is bpm", "ถาม what is bpm"])
def test_everyone_can_ask(arg):
    e = _engine()
    commands._ai_command(e, _msg(), arg, False)
    e.ai_ask.assert_called_once_with("zdevz", "what is bpm")


def test_ask_needs_a_question():
    e = _engine()
    with pytest.raises(UserError, match="ai_ask_usage"):
        commands._ai_command(e, _msg(), "ask", False)
    e.ai_ask.assert_not_called()


def test_ask_without_key_says_why():
    e = _engine(key="")
    with pytest.raises(UserError, match="chatbot_ai_unavailable"):
        commands._ai_command(e, _msg(), "ask hello", False)
    e.ai_ask.assert_not_called()


def test_ask_when_disabled():
    e = _engine(enabled=False)
    with pytest.raises(UserError, match="ai_disabled"):
        commands._ai_command(e, _msg(), "ask hello", False)


@pytest.mark.parametrize("arg", ["on", "off", "status", "model x", "prompt y", "help", ""])
def test_settings_are_admin_only(arg):
    e = _engine()
    with pytest.raises(UserError, match="ai_ask_usage"):
        commands._ai_command(e, _msg(), arg, False)
    assert e.cfg.ai_enabled is True and e.cfg.ai_model == Config().ai_model
    e.say.assert_not_called()


def test_on_without_key_does_not_claim_enabled():
    e = _engine(key="")
    commands._ai_command(e, _msg(), "on", True)
    e.say.assert_called_once_with("chatbot_ai_unavailable")


def test_on_with_key():
    e = _engine(enabled=False)
    commands._ai_command(e, _msg(), "on", True)
    e.say.assert_called_once_with("ai_enabled")


def test_status_without_key_names_the_missing_key():
    e = _engine(key="")
    commands._ai_command(e, _msg(), "status", True)
    assert "ai_no_key" in e.say.call_args[0][0]


def test_reply_is_addressed_and_error_is_reported():
    fake = Mock()
    fake._ai_inflight = 1
    fake._ai_inflight_lock = __import__("threading").Lock()
    fake.t.side_effect = lambda k, **kw: k
    fake.ai.chat.return_value = "!skip haha"
    Engine._ai_reply(fake, "bob", "q")
    fake.say.assert_called_with("bob: !skip haha")  # never starts with the prefix
    fake.ai.chat.return_value = None
    Engine._ai_reply(fake, "bob", "q")
    fake.say.assert_called_with("bob: chatbot_ai_error")
    assert fake._ai_inflight == -1


def test_client_strips_reasoning_and_leaves_room_for_the_answer(monkeypatch):
    c = AIClient(Config(ai_api_key="k"))
    sent = {}

    def post(url, payload):
        sent.update(payload)
        return {"choices": [{"message": {"content": "<think>long reasoning</think>\nสวัสดีครับ"}}]}

    monkeypatch.setattr(c, "_post_json", post)
    assert c.chat("hi") == "สวัสดีครับ"
    assert sent["max_tokens"] >= 1024


def test_client_unfinished_reasoning_is_no_answer(monkeypatch):
    c = AIClient(Config(ai_api_key="k"))
    monkeypatch.setattr(
        c, "_post_json", lambda u, p: {"choices": [{"message": {"content": "<think>cut off"}}]}
    )
    assert c.chat("hi") is None


def test_help_without_im_window_tells_the_user():
    """Live 2026-11-23: `!ai help` with no IM window open was dropped silently."""
    e = _engine()
    e.send_im.return_value = False
    with pytest.raises(UserError, match="ai_help_no_im"):
        commands._ai_command(e, _msg(), "help", True)
    e.send_im.return_value = True
    commands._ai_command(e, _msg(), "help", True)  # sent: nothing posted in the room
    e.say.assert_not_called()
