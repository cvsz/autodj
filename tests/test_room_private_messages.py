"""Private messages shown inside the room pane reach the bot as IMs.

Live 2026-11-27 11:03 (Camfrog web room): private messages are groups in the room
history ("ข้อความส่วนตัวจาก" + linked nick + time + body), not separate IM
windows; the parser dropped them all and the IM tab stayed empty.
Items below are the real UIA items read from the live room pane.
"""

from __future__ import annotations

import re

from autodj.adapters import uia
from autodj.adapters.base import compile_join_rx
from autodj.config import Config
from autodj.webchat import items_to_lines

LIVE = [
    ("avatar", ""), ("text", "ZeazBot"), ("text", "11:03"), ("text", "Hello, owner Seaza!"),
    ("avatar", ""), ("text", "ข้อความส่วนตัวจาก"), ("link", "ZeazBot"), ("text", "11:03"),
    ("text", "พิมพ์ bot เพื่อขอ 8 ลูกบอล"),
    ("avatar", ""), ("text", "ข้อความส่วนตัวจาก"), ("link", "ZeazBot"), ("text", "11:03"),
    ("text", "ไมค์ในห้องนี้จัดการโดย DJ Manager"),
    ("text", "โปรดตรวจสอบ !DJ HELP หรือเพิ่มตัวคุณเองในคิวของ DJ โดยใช้ !DJ ADD"),
    ("avatar", ""), ("text", "Seaza"), ("text", "11:05"),
    ("text", "อย่าลืมโหวตข้ามเพลงที่ไม่ถูกใจด้วยคำสั่ง !โหวตข้าม"),
]  # fmt: skip


def _adapter() -> uia.UiaAdapter:
    a = uia.UiaAdapter.__new__(uia.UiaAdapter)
    a.cfg = Config()
    a.rx = re.compile(a.cfg.line_regex)
    a.join_rx = compile_join_rx(a.cfg.join_line_regex)
    return a


def test_private_groups_become_im_lines():
    assert items_to_lines(LIVE) == [
        "11:03 ZeazBot: Hello, owner Seaza!",
        "11:03 IM ZeazBot: พิมพ์ bot เพื่อขอ 8 ลูกบอล",
        "11:03 IM ZeazBot: ไมค์ในห้องนี้จัดการโดย DJ Manager "
        "โปรดตรวจสอบ !DJ HELP หรือเพิ่มตัวคุณเองในคิวของ DJ โดยใช้ !DJ ADD",
        "11:05 Seaza: อย่าลืมโหวตข้ามเพลงที่ไม่ถูกใจด้วยคำสั่ง !โหวตข้าม",
    ]


def test_private_lines_reach_the_engine_as_ims():
    a = _adapter()
    lines = items_to_lines(LIVE)
    msgs = [a._room_line_message(ln) for ln in lines]
    assert [(m.user, m.is_im) for m in msgs] == [
        ("ZeazBot", False),
        ("ZeazBot", True),
        ("ZeazBot", True),
        ("Seaza", False),
    ]
    assert msgs[1].text == "พิมพ์ bot เพื่อขอ 8 ลูกบอล"


def test_english_header_and_outgoing_private_messages():
    items = [
        ("avatar", ""), ("text", "Private message from:"), ("link", "amy"), ("text", "9:15 PM"),
        ("text", "!play song"),
        ("avatar", ""), ("text", "ข้อความส่วนตัวถึง"), ("link", "amy"), ("text", "9:16 PM"),
        ("text", "our own reply"),
    ]  # fmt: skip
    assert items_to_lines(items) == ["9:15 PM IM amy: !play song"]


def test_room_bot_im_is_shown_but_never_answered_or_run():
    from test_core import FakeAdapter, FakePlayer, out

    from autodj.adapters.base import ChatMessage
    from autodj.engine import Engine

    sent = []

    class Im(FakeAdapter):
        def send_im(self, user, text):
            sent.append((user, text))

    e = Engine(
        Config(lang="th", im_auto_reply_enabled=True, im_require_room_presence=False),
        Im(),
        player=FakePlayer(),
        index=None,
    )
    e._active_room_users.add("zeazbot")
    e._handle_im(ChatMessage("ZeazBot", "!play x", is_im=True))
    assert e.im_log[-1] == ("ZeazBot", "!play x")  # in the IM tab
    assert sent == [] and out(e) == []  # no reply, no command
    e.exec.shutdown(wait=True)
    assert len(e.queue.requests) == 0


def test_a_nick_link_without_the_header_is_unchanged():
    items = [("avatar", ""), ("link", "amy"), ("text", "9:15"), ("text", "hello")]
    assert items_to_lines(items) == ["9:15 amy: hello"]
