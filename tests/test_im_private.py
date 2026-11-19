"""IM traffic never reaches the room: not the room chat log, not a room post."""

from autodj.adapters import NullAdapter
from autodj.adapters.base import ChatMessage
from autodj.config import Config
from autodj.engine import Engine


def _im(user: str, text: str) -> ChatMessage:
    return ChatMessage(user, text, is_im=True)


def _engine():
    e = Engine(Config(im_auto_reply_enabled=True, im_auto_reply_message="away"), NullAdapter())
    room: list[str] = []
    e.say = lambda text, *a, **k: room.append(text) or True  # type: ignore[method-assign]
    return e, room


def test_im_not_in_room_chat_log_or_room():
    e, room = _engine()
    e._handle_im(_im("zdevz", "secret hello"))
    assert room == []
    assert not any("secret hello" in str(entry) for entry in e.chat_snapshot()[2])


def test_im_auto_reply_uses_private_channel_when_available():
    e, room = _engine()
    sent: list[tuple[str, str]] = []
    e.adapter.send_im = lambda user, text: sent.append((user, text))  # type: ignore[attr-defined]
    e._update_participant_count("zdevz")  # the sender is in the room
    e._handle_im(_im("zdevz", "hi"))
    assert sent == [("zdevz", "away")]
    assert room == []
