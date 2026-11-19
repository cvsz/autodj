"""About text carries the credit line; Composite exposes the reader's send_im."""

import autodj
from autodj.adapters import Composite, NullAdapter


def test_about_text_has_credit_and_version():
    text = autodj.about_text()
    assert "camfrog:add:Seaza Dev @ZEAZDEV COMPANY LIMITED" in text
    assert autodj.__version__ in text


def test_composite_forwards_send_im_from_reader():
    sent: list[tuple[str, str]] = []
    reader, sender = NullAdapter(), NullAdapter()
    reader.send_im = lambda user, text: sent.append((user, text))  # type: ignore[attr-defined]
    c = Composite(reader, sender)
    assert callable(c.send_im)
    c.send_im("zdevz", "hi")
    assert sent == [("zdevz", "hi")]


def test_composite_without_private_channel_reports_none():
    assert Composite(NullAdapter(), NullAdapter()).send_im is None


def test_engine_im_reply_goes_through_composite():
    from autodj.adapters.base import ChatMessage
    from autodj.config import Config
    from autodj.engine import Engine

    sent: list[tuple[str, str]] = []
    reader = NullAdapter()
    reader.send_im = lambda user, text: sent.append((user, text))  # type: ignore[attr-defined]
    e = Engine(Config(room="ZeaZDev", lang="th"), Composite(reader, NullAdapter()))
    e._handle_im(ChatMessage("zdevz", "!play x", is_im=True))
    assert sent == [("zdevz", "กรุณาเข้าห้อง ZeaZDev ก่อนถึงสามารถขอเพลงได้")]
