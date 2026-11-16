"""Item sequences shaped like a real Camfrog room dump (avatar = Image with empty name)."""

import re

from camfrog_autodj.adapters.base import parse_line
from camfrog_autodj.config import Config
from camfrog_autodj.webchat import items_to_lines

A = ("avatar", "")
RX = re.compile(Config().line_regex)


def t(n):
    return ("text", n)


def link(n):
    return ("link", n)


def parsed(items, strict=True):
    return [
        (m.user, m.text) for m in (parse_line(x, RX) for x in items_to_lines(items, strict)) if m
    ]


def test_basic_and_partial_head_skipped():
    items = [
        t("cut-off tail of old msg"),
        t("9:99x"),
        A,
        t("ZeazBot"),
        t("4:02"),
        t("Hello, user Omegaria!"),
        A,
        link("zdevz"),
        t("5:44"),
        t("!musiceandom"),
    ]
    assert parsed(items) == [
        ("ZeazBot", "Hello, user Omegaria!"),
        ("zdevz", "!musiceandom"),
    ]


def test_image_only_message_dropped():
    items = [A, link("Zeasa"), t("5:44"), A, link("zdevz"), t("5:44"), t("!skip")]
    assert parsed(items) == [("zdevz", "!skip")]


def test_system_line_not_glued_to_previous_body():
    items = [
        A,
        link("Seaza"),
        t("12:22"),
        t("."),
        t("SYSTEM LINE"),
        A,
        link("zdevz"),
        t("12:22"),
        t("!skip"),
    ]
    assert parsed(items) == [("Seaza", "."), ("zdevz", "!skip")]
    assert parsed(items, strict=False)[0] == ("Seaza", ". SYSTEM LINE")


def test_date_header_between_messages():
    items = [
        A,
        link("zdevz"),
        t("11:59"),
        t("!np"),
        t("Monday, 27 October"),
        A,
        link("zdevz"),
        t("0:01"),
        t("!queue"),
    ]
    assert parsed(items) == [("zdevz", "!np"), ("zdevz", "!queue")]


def test_time_like_body_is_not_a_new_message():
    items = [A, link("bob"), t("5:00"), t("10:30"), A, link("zdevz"), t("5:01"), t("!np")]
    assert parsed(items) == [("bob", "10:30"), ("zdevz", "!np")]


def test_emoticon_and_link_continue_body():
    items = [
        A,
        link("bob"),
        t("5:00"),
        t("!play"),
        ("emo", "Smile :)"),
        t("https://youtu.be/x"),
        A,
        link("zdevz"),
        t("5:01"),
        t("!np"),
    ]
    assert parsed(items)[0] == ("bob", "!play https://youtu.be/x")
    items = [A, link("bob"), t("5:00"), t("!play"), link("https://youtu.be/x"), t("rest")]
    assert parsed(items) == [("bob", "!play https://youtu.be/x rest")]
