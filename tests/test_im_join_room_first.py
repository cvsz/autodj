"""IMs from outside the room get a private 'join the room first' notice; nothing reaches the room."""

from camfrog_autodj.adapters import NullAdapter
from camfrog_autodj.adapters.base import ChatMessage
from camfrog_autodj.config import Config
from camfrog_autodj.engine import Engine


def _engine(lang: str = "th"):
    cfg = Config(
        room="ZeaZDev", lang=lang, im_auto_reply_enabled=False, im_require_room_presence=True
    )
    e = Engine(cfg, NullAdapter())
    room: list[str] = []
    ims: list[tuple[str, str]] = []
    e.say = lambda text, *a, **k: room.append(text) or True  # type: ignore[method-assign]
    e.adapter.send_im = lambda user, text: ims.append((user, text))  # type: ignore[attr-defined]
    return e, room, ims


def test_outsider_im_gets_private_join_notice_once():
    e, room, ims = _engine()
    for _ in range(3):
        e._handle_im(ChatMessage("zdevz", "!play เพลงรัก", is_im=True))
    assert ims == [("zdevz", "กรุณาเข้าห้อง ZeaZDev ก่อนถึงสามารถขอเพลงได้")]
    assert room == []
    assert e._is_echo("กรุณาเข้าห้อง ZeaZDev ก่อนถึงสามารถขอเพลงได้")  # read-back is ignored


def test_user_in_room_gets_no_join_notice():
    e, room, ims = _engine()
    e._update_participant_count("zdevz")
    e._handle_im(ChatMessage("zdevz", "hello", is_im=True))
    assert ims == []


def test_join_notice_shows_in_im_viewer():
    e, _room, _ims = _engine()
    e._handle_im(ChatMessage("zdevz", "!play x", is_im=True))
    _seq, _ver, log_entries = e.im_snapshot()
    assert any("กรุณาเข้าห้อง" in text for _who, text in log_entries)


def test_no_private_channel_means_no_reply_anywhere():
    cfg = Config(room="ZeaZDev", im_require_room_presence=True)
    e = Engine(cfg, NullAdapter())
    room: list[str] = []
    e.say = lambda text, *a, **k: room.append(text) or True  # type: ignore[method-assign]
    e._handle_im(ChatMessage("zdevz", "!play x", is_im=True))
    assert room == []
