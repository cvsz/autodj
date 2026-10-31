"""Tests for camfrog_autodj/discover.py — auto-discovery of Camfrog room window
and safe config.toml editing (backup, atomic write, TOML re-validation)."""

from __future__ import annotations

import re

from camfrog_autodj.config import Config
from camfrog_autodj.discover import (
    Ctl,
    Found,
    choose_input,
    choose_view,
    save_config,
    score_web,
    score_window,
    to_updates,
    update_config_text,
)


# ------------------------------------------------------------ choose_view ---
def test_choose_view_picks_document_with_most_matching_lines():
    rx = re.compile(Config().line_regex)
    ctls = [
        Ctl("Document", 0, "alice: hi\nbob: yo\n", 0, 0, 100, 50),
        Ctl("Document", 1, "not a chat line\nanother\n", 0, 0, 200, 80),
        Ctl("Edit", 0, "type here", 0, 0, 50, 20),
    ]
    view, matched = choose_view(ctls, rx)
    assert view is not None and view.index == 0
    assert matched == 2


def test_choose_view_returns_none_when_no_match():
    rx = re.compile(Config().line_regex)
    ctls = [Ctl("Edit", 0, "", 0, 0, 50, 20)]
    view, matched = choose_view(ctls, rx)
    assert view is None and matched == 0


# ------------------------------------------------------------ choose_input ---
def test_choose_input_picks_lowest_widest_edit():
    view = Ctl("Document", 0, "alice: hi", 0, 0, 100, 50)
    ctls = [
        Ctl("Edit", 0, "", 0, 0, 100, 30),
        Ctl("Edit", 1, "", 0, 520, 300, 40),
        Ctl("Edit", 2, "", 0, 520, 200, 40),
    ]
    inp = choose_input(ctls, view)
    assert inp is not None and inp.index == 1  # lowest (top=520), widest (width=300)


def test_choose_input_excludes_the_view_control():
    view = Ctl("Document", 0, "alice: hi", 0, 0, 100, 50)
    ctls = [Ctl("Document", 0, "alice: hi", 0, 0, 100, 50)]
    inp = choose_input(ctls, view)
    assert inp is None


# ------------------------------------------------------------ score_window ---
def test_score_window_returns_found_when_view_and_input():
    rx = re.compile(Config().line_regex)
    view = Ctl("Document", 0, "alice: hi\n", 0, 0, 100, 50)
    inp = Ctl("Edit", 0, "", 0, 520, 200, 40)
    f = score_window("My Room", [view, inp], rx)
    assert f is not None and f.web is False and f.matched == 1


def test_score_window_returns_none_when_no_view():
    rx = re.compile(Config().line_regex)
    ctls = [Ctl("Edit", 0, "", 0, 0, 100, 30)]
    assert score_window("My Room", ctls, rx) is None


# ------------------------------------------------------------ score_web ---
def test_score_web_returns_none_when_no_panes(monkeypatch):
    from camfrog_autodj import webchat

    monkeypatch.setattr(webchat, "find_web_panes", lambda win, vt, it: (None, None))
    cfg = Config()
    rx = re.compile(cfg.line_regex)
    fake_win = object()
    assert score_web("title", fake_win, cfg, rx) is None


# ------------------------------------------------------------ to_updates ---
def test_to_updates_web_and_text():
    rx = re.compile(Config().line_regex)
    web_f = Found("ZeaZDev: x", Ctl("Pane", 0), Ctl("Pane", 0), 5, web=True)
    assert to_updates(web_f) == {
        "window_title_re": re.escape("ZeaZDev: x"),
        "view_kind": "web",
    }

    text_f = Found(
        "My Room",
        Ctl("Document", 0, "", 0, 0, 100, 50),
        Ctl("Edit", 0, "", 0, 520, 200, 40),
        3,
    )
    ups = to_updates(text_f)
    assert ups["view_type"] == "Document" and ups["view_index"] == 0
    assert ups["input_type"] == "Edit" and ups["input_index"] == 0


# ------------------------------------------------------------ update_config_text ---
def test_update_config_text_replaces_existing_key():
    text = 'bot_nick = "AutoDJ"\nlog_file = ""\n'
    new = update_config_text(text, {"log_file": "autodj.log"})
    assert "log_file = 'autodj.log'" in new
    assert 'bot_nick = "AutoDJ"' in new


def test_update_config_text_appends_missing_key():
    text = 'bot_nick = "AutoDJ"\n'
    new = update_config_text(text, {"playlist_file": "playlist.json"})
    assert "playlist_file = 'playlist.json'" in new


def test_update_config_text_keeps_comment():
    text = 'log_file = ""   # comment here\n'
    new = update_config_text(text, {"log_file": "autodj.log"})
    assert new.strip().endswith("# comment here")


# ------------------------------------------------------------ save_config ---
def test_save_config_atomic_and_backup(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text('bot_nick = "X"\n', "utf-8")
    assert save_config(str(p), {"log_file": "autodj.log"}) is True
    assert (p.with_name("config.toml.bak")).exists()
    c = Config.load(str(p))
    assert c.log_file == "autodj.log"


def test_save_config_refuses_invalid_toml(tmp_path):
    from camfrog_autodj.discover import save_config

    p = tmp_path / "config.toml"
    p.write_text('bot_nick = "X"\n', "utf-8")
    # a value with a raw newline would be invalid TOML: must be refused
    assert save_config(str(p), {"window_title_re": "tab\there\nnewline"}) is True
    c = Config.load(str(p))
    assert c.window_title_re == "tab\there\nnewline"


def test_save_config_no_change_returns_false(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("bot_nick = 'X'\nlog_file = 'autodj.log'\n", "utf-8")
    assert save_config(str(p), {"log_file": "autodj.log"}) is False
