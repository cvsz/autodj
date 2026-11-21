"""Admin room commands take exactly one target token.

Before, "!kick bob extra" sent "/kick bob extra" to the room, and a target
could carry a second slash command.  _single_target() rejects whitespace,
control characters, "/" and anything over 64 characters, and nothing is sent.
"""

from __future__ import annotations

import pytest
from test_core import make, out

from autodj.adapters.base import ChatMessage


def _run(text: str) -> list[str]:
    e = make()
    e.router.handle(ChatMessage("Boss", text))
    return out(e)


@pytest.mark.parametrize(
    ("cmd", "sent"),
    [
        ("!kick bob", "/kick bob"),
        ("!ban bob", "/ban bob"),
        ("!unban bob", "/unban bob"),
        ("!punish bob", "/punish bob"),
        ("!kick สมชาย", "/kick สมชาย"),  # Thai nicks are valid Camfrog nicks
        ("!kick  bob  ", "/kick bob"),  # surrounding spaces are trimmed
    ],
)
def test_single_token_target_is_sent(cmd, sent):
    assert sent in _run(cmd)


@pytest.mark.parametrize(
    "cmd",
    [
        "!kick bob extra",
        "!ban bob /kick amy",
        "!punish bob\tamy",
        "!unban a/b",
        "!kick " + "x" * 65,
        "!kick bob\x07",
    ],
)
def test_unsafe_target_sends_no_room_command(cmd):
    sent = _run(cmd)
    assert not any(s.startswith("/") for s in sent), sent


def test_unsafe_target_returns_usage():
    sent = _run("!kick bob extra")
    assert any("kick" in s for s in sent), sent  # usage message, not a command


def test_target_of_exactly_64_chars_is_accepted():
    nick = "x" * 64
    assert f"/kick {nick}" in _run(f"!kick {nick}")


def test_punishbot_logs_and_sends_punish():
    sent = _run("!punishbot spambot")
    assert "/punish spambot" in sent
