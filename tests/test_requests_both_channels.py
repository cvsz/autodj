"""Requests work in room chat and by IM, but only from users in the room."""

from autodj.adapters import NullAdapter
from autodj.adapters.base import ChatMessage
from autodj.config import Config
from autodj.engine import Engine
from autodj.models import Track


def _engine():
    e = Engine(Config(room="ZeaZDev", welcome_message_enabled=False), NullAdapter())
    room: list[str] = []
    ims: list[tuple[str, str]] = []
    routed: list[str] = []
    e.say = lambda text, *a, **k: room.append(text) or True  # type: ignore[method-assign]
    e.adapter.send_im = lambda user, text: ims.append((user, text))  # type: ignore[attr-defined]
    e.resolve = lambda arg, user, admin: [Track(f"https://youtu.be/{arg}", arg, 200, user)]  # type: ignore[method-assign]
    return e, room, ims, routed


def test_default_allows_room_requests():
    assert Config().allow_play_in_room is True


def test_room_request_is_queued():
    e, room, _ims, _ = _engine()
    e._handle_room_message(ChatMessage("amy", "!play song1"))
    e.exec.shutdown(wait=True)
    assert [t.title for t in e.queue.requests] == ["song1"]
    assert "amy" in e._active_room_users  # typing in the room = present


def test_im_request_from_user_in_room_is_queued():
    e, _room, ims, _ = _engine()
    e._update_participant_count("zdevz")
    e._handle_im(ChatMessage("zdevz", "!play song2", is_im=True))
    e.exec.shutdown(wait=True)
    assert [t.title for t in e.queue.requests] == ["song2"]


def test_im_request_from_outside_gets_join_text_and_is_not_queued():
    e, room, ims, _ = _engine()
    e._handle_im(ChatMessage("stranger", "!play song3", is_im=True))
    e.exec.shutdown(wait=True)
    assert e.queue.requests == [] or not list(e.queue.requests)
    assert ims == [("stranger", "กรุณาเข้าห้อง camfrog:join:ZeaZDev ก่อนขอเพลงครับ")]
    assert room == []
