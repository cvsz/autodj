"""An IM is acted on only when its sender is in the room."""

from autodj.adapters import NullAdapter
from autodj.adapters.base import ChatMessage
from autodj.config import Config
from autodj.engine import Engine


def _engine():
    cfg = Config(admins=["boss"], im_auto_reply_enabled=True, im_auto_reply_message="away")
    e = Engine(cfg, NullAdapter())
    routed: list[str] = []
    sent: list[tuple[str, str]] = []
    e.exec.submit = lambda fn, msg, *a, **k: routed.append(msg.text)  # type: ignore[method-assign]
    e.adapter.send_im = lambda user, text: sent.append((user, text))  # type: ignore[attr-defined]
    return e, routed, sent


def _im(user: str, text: str) -> ChatMessage:
    return ChatMessage(user, text, is_im=True)


def test_im_from_outside_room_is_ignored_but_shown_in_viewer():
    e, routed, sent = _engine()
    e._handle_im(_im("stranger", "play x"))
    assert routed == []  # not executed...
    assert sent == [("stranger", "กรุณาเข้าห้อง ก่อนขอเพลงครับ")]  # ...answered privately
    assert ("stranger", "play x") in e.im_snapshot()[2]


def test_admin_outside_room_is_ignored_too():
    e, routed, _sent = _engine()
    e._handle_im(_im("boss", "skip"))
    assert routed == []


def test_im_from_user_in_room_is_handled():
    e, routed, sent = _engine()
    e._update_participant_count("Amy")
    e._handle_im(_im("amy", "play x"))
    assert routed == ["play x"]
    assert sent == [("amy", "away")]


def test_presence_check_can_be_disabled():
    e, routed, _sent = _engine()
    e.cfg.im_require_room_presence = False
    e._handle_im(_im("stranger", "play x"))
    assert routed == ["play x"]
