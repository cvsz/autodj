"""Room greeting by permission: admin greeting, user welcome, blocked users ignored."""

from camfrog_autodj.adapters import NullAdapter
from camfrog_autodj.config import Config
from camfrog_autodj.engine import Engine


def _engine(**cfg_kw):
    cfg = Config(room="ZeaZDev", admins=["boss"], blocked_users=["spammer"], **cfg_kw)
    e = Engine(cfg, NullAdapter())
    said: list[str] = []
    e.say = lambda text, *a, **k: said.append(text) or True  # type: ignore[method-assign]
    return e, said


def test_default_welcome_text():
    e, said = _engine()
    assert e._greet_user("amy") is True
    assert said == ["ยินดีต้อนรับ amy เข้าสู่ ZeaZDev สถานีเพลง อัตโนมัติ 24/7 ชั่วโมง"]


def test_admin_gets_admin_greeting_not_welcome():
    e, said = _engine()
    assert e._greet_user("Boss") is True
    assert said and "boss".lower() in said[0].lower() and "สถานีเพลง" not in said[0]


def test_blocked_user_is_never_greeted():
    e, said = _engine()
    assert e._greet_user("Spammer") is False
    assert said == []


def test_welcome_respects_cooldown():
    e, said = _engine()
    e._greet_user("amy")
    e._greet_user("amy")
    assert len(said) == 1


def test_welcome_without_room_name_has_no_double_space():
    from camfrog_autodj.adapters import NullAdapter
    from camfrog_autodj.adapters.base import ChatMessage
    from camfrog_autodj.config import Config
    from camfrog_autodj.engine import Engine

    e = Engine(Config(), NullAdapter())
    e.cfg.room = ""
    said: list[str] = []
    e.say = lambda text, *a, **k: said.append(text) or True  # type: ignore[method-assign]
    assert e._handle_welcome_message(ChatMessage("amy", "hi"))
    assert said and "  " not in said[0] and "amy" in said[0]
