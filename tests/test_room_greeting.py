"""Greeting users when they enter the room (join notice) or first speak."""

import threading

from test_core import make, out

from autodj.adapters.base import ChatMessage, compile_join_rx, parse_join
from autodj.config import Config


def _join(user: str) -> ChatMessage:
    return ChatMessage(user, "", event="join")


def test_default_join_regex_matches_room_notices_only():
    rx = compile_join_rx(Config().join_line_regex)
    cases = {
        "*** bob has joined the room": "bob",
        "bob has entered the room": "bob",
        "[12:01] Amy_99 has joined": "Amy_99",
        "สมชาย เข้าสู่ห้อง": "สมชาย",
        "*** สมชาย ได้เข้าห้อง": "สมชาย",
    }
    for line, user in cases.items():
        m = parse_join(line, rx)
        assert m is not None and m.user == user and m.event == "join", line
    for line in ("bob: hello", "I have joined a club", "random text", ""):
        assert parse_join(line, rx) is None, line
    assert compile_join_rx("") is None  # empty disables detection
    assert parse_join("*** bob has joined the room", None) is None


def test_user_is_greeted_by_name_when_entering_the_room():
    e = make()
    e.cfg.welcome_message_message = "สวัสดีครับคุณ {user} ยินดีต้อนรับเข้าห้อง {room}"
    e.cfg.room = "MusicRoom"
    e._handle_room_join(_join("amy"))
    assert out(e) == ["สวัสดีครับคุณ amy ยินดีต้อนรับเข้าห้อง MusicRoom"]
    assert "amy" in e._active_room_users  # counts as present (IM presence checks)

    e._handle_room_join(_join("amy"))  # re-join inside the cooldown
    e.cfg.np_question_keywords = []
    e._handle_room_message(ChatMessage("amy", "hello everyone"))  # then speaks
    assert out(e) == []  # one greeting per visit


def test_admin_entering_gets_the_admin_greeting_not_the_welcome():
    e = make()
    e.cfg.admin_greeting_message = "Welcome back admin {admin}"
    e._handle_room_join(_join("Boss"))
    assert out(e) == ["Welcome back admin Boss"]


def test_first_message_still_greets_when_no_join_notice_is_seen():
    e = make()
    e.cfg.welcome_message_message = "hi {user}"
    e.cfg.np_question_keywords = []
    e._handle_room_message(ChatMessage("carl", "yo"))
    assert "hi carl" in out(e)


def test_greeting_text_with_stray_braces_never_raises():
    e = make()
    e.cfg.welcome_message_message = "{user} welcome {party} }{"
    e._handle_room_join(_join("dee"))
    assert out(e) == ["dee welcome {party} }{"]


def test_disabled_welcome_sends_nothing_on_join():
    e = make()
    e.cfg.welcome_message_enabled = False
    e._handle_room_join(_join("eve"))
    assert out(e) == []


def test_chat_loop_routes_join_events_without_running_commands():
    e = make()
    e.cfg.welcome_message_message = "hi {user}"
    handled: list[ChatMessage] = []
    e.router.handle = handled.append  # type: ignore[method-assign]
    e.adapter.messages = lambda: iter([_join("finn")])  # type: ignore[method-assign]
    t = threading.Thread(target=e._chat_loop)
    t.start()
    t.join(timeout=5)
    assert out(e) == ["hi finn"]
    assert handled == []  # a join notice is not a command
