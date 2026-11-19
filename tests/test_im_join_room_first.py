"""IMs from outside the room get a private 'join the room first' notice; nothing reaches the room."""

from autodj.adapters import NullAdapter
from autodj.adapters.base import ChatMessage
from autodj.config import Config
from autodj.engine import Engine


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
    assert ims == [("zdevz", "กรุณาเข้าห้อง camfrog:join:ZeaZDev ก่อนขอเพลงครับ")]
    assert room == []
    assert e._is_echo("กรุณาเข้าห้อง camfrog:join:ZeaZDev ก่อนขอเพลงครับ")  # read-back is ignored


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


def test_join_notice_cooldowns_stay_bounded_without_cleanup_loop():
    e, _room, _ims = _engine()  # im_auto_reply_enabled=False: no cleanup loop
    for i in range(1200):
        e._im_reply_cooldowns[f"join:old{i}"] = -1e9  # long expired
    e._handle_im(ChatMessage("zdevz", "!play x", is_im=True))
    assert len(e._im_reply_cooldowns) < 10


def test_join_message_is_configurable_and_language_independent():
    for lang in ("en", "th"):
        e, _room, ims = _engine(lang)
        e.cfg.im_join_room_message = "join {room} first, {user}"
        e._handle_im(ChatMessage("zdevz", "!play x", is_im=True))
        assert ims == [("zdevz", "join ZeaZDev first, zdevz")]


def test_empty_join_message_sends_nothing():
    e, _room, ims = _engine()
    e.cfg.im_join_room_message = ""
    e._handle_im(ChatMessage("zdevz", "!play x", is_im=True))
    assert ims == []
