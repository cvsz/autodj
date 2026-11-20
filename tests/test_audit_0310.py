"""Regression tests for the v0.3.10 audit fixes."""

import types

from test_core import FakeAdapter, FakePlayer, make, out

from autodj import __main__ as main_mod
from autodj.adapters.base import ChatMessage
from autodj.config import Config
from autodj.engine import Engine

# ---- mic greeting ---------------------------------------------------------


def _mic_engine(**kw):
    cfg = Config(mic_greeting_enabled=True, mic_greeting_cooldown=0, **kw)
    return Engine(cfg, FakeAdapter(), player=FakePlayer(), index=None)


def test_mic_notice_from_named_user_greets_them():
    e = _mic_engine()
    e._handle_re_events(ChatMessage("Seaza", "Seaza is now speaking"))
    assert out(e) == ["Seaza is now the DJ."]


def test_mic_notice_thai_phrase():
    e = _mic_engine(lang="th")
    e._handle_re_events(ChatMessage("Seaza", "Seaza กำลังรับไมค์"))
    assert out(e) == ["คุณ Seaza รับไมค์เป็น DJ ขณะนี้"]


def test_ordinary_chat_does_not_trigger_mic_greeting():
    e = _mic_engine()
    for text in ("who is the dj?", "is the dj here", "ใครกำลังพูดอยู่", "กำลังพูด", "lol has the mic"):
        e._handle_re_events(ChatMessage("amy", text))
    assert out(e) == []


def test_user_cannot_announce_someone_else_as_dj():
    e = _mic_engine()
    e._handle_re_events(ChatMessage("amy", "Bob is now speaking"))
    assert out(e) == []


def test_mic_greeting_custom_template_and_bad_template_fallback():
    e = _mic_engine(mic_greeting_message="DJ {user} on air!")
    e._handle_re_events(ChatMessage("Seaza", "Seaza is now speaking"))
    assert out(e) == ["DJ Seaza on air!"]
    e = _mic_engine(mic_greeting_message="bad {nick}")
    e._handle_re_events(ChatMessage("Seaza", "Seaza is now speaking"))
    assert out(e) == ["Seaza is now the DJ."]


def test_mic_greeting_keys_in_example_config():
    import tomllib

    with open("config.example.toml", "rb") as fh:
        ex = tomllib.load(fh)
    c = Config()
    for key in ("mic_greeting_enabled", "mic_greeting_message", "mic_greeting_cooldown"):
        assert ex[key] == getattr(c, key), key


# ---- echo detection -------------------------------------------------------


def test_say_does_not_double_remember():
    e = make()
    e.say("hello room")
    assert len(e._sent) == 0  # remembered by _sender() right before posting


def test_same_line_posted_twice_both_echoes_ignored():
    e = make()
    e._remember_sent("Now playing: song")
    e._remember_sent("Now playing: song")
    assert e._is_echo("Now playing: song")
    assert e._is_echo("Now playing: song")
    assert not e._is_echo("Now playing: song")


# ---- comtypes gen cache cleanup -------------------------------------------


def test_comtypes_cleanup_only_removes_generated_modules(tmp_path, monkeypatch):
    import logging
    import sys

    gen = tmp_path / "gen"
    gen.mkdir()
    (gen / "__init__.py").write_text("")
    (gen / "_00020430_0000_0000_C000_000000000046_0_2_0.py").write_text("broken(")
    (gen / "stdole.py").write_text("")
    (gen / "__pycache__").mkdir()
    (gen / "keep.txt").write_text("x")
    pkg_file = tmp_path / "client.py"  # stands in for the comtypes package itself
    pkg_file.write_text("")

    fake_client = types.ModuleType("comtypes.client")
    fake_client.gen_dir = str(gen)  # type: ignore[attr-defined]
    fake_pkg = types.ModuleType("comtypes")
    fake_pkg.client = fake_client  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "comtypes", fake_pkg)
    monkeypatch.setitem(sys.modules, "comtypes.client", fake_client)

    removed = main_mod._clean_comtypes_gen_cache(logging.getLogger("t"))

    assert len(removed) == 3
    assert sorted(p.name for p in gen.iterdir()) == ["__init__.py", "keep.txt"]
    assert pkg_file.exists()


def test_comtypes_cleanup_without_gen_dir_is_noop(monkeypatch):
    import logging
    import sys

    fake_client = types.ModuleType("comtypes.client")
    fake_client.gen_dir = None  # type: ignore[attr-defined]
    fake_pkg = types.ModuleType("comtypes")
    fake_pkg.client = fake_client  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "comtypes", fake_pkg)
    monkeypatch.setitem(sys.modules, "comtypes.client", fake_client)
    assert main_mod._clean_comtypes_gen_cache(logging.getLogger("t")) == []
