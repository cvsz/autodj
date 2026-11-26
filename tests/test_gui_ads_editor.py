"""Settings -> Ads list editor: the edit model and a real Tk window round trip."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from types import SimpleNamespace

import pytest

from autodj import ads_list
from autodj.config import Config
from autodj.gui_ads import AdsDraft, AdsEditor
from autodj.messages import tr


def test_draft_add_update_delete_move():
    d = AdsDraft(["a", "b"])
    assert not d.dirty
    assert d.add("  c\nline two ") == 2
    assert d.items == ["a", "b", "c line two"] and d.dirty
    assert d.update(0, "A") == 0
    assert d.move(0, 1) == 1 and d.items[:2] == ["b", "A"]
    assert d.move(0, -1) == 0  # already first: unchanged
    assert d.delete(2) == 1 and d.items == ["b", "A"]
    assert d.delete(0) == 0 and d.delete(0) is None and d.items == []


def test_draft_rejects_empty_and_too_long():
    d = AdsDraft([])
    with pytest.raises(ValueError):
        d.add("   \n ")
    with pytest.raises(ValueError):
        d.add("x" * (ads_list.MAX_AD_CHARS + 1))
    assert d.items == [] and not d.dirty


def test_draft_save_clears_dirty(tmp_path):
    p = tmp_path / "ads-list.json"
    d = AdsDraft([])
    d.add("hello")
    d.save(str(p))
    assert not d.dirty and ads_list.load(str(p)) == ["hello"]


def _root():
    try:
        root = tk.Tk()
    except tk.TclError as ex:  # no display (CI on Linux without Xvfb)
        pytest.skip(f"no Tk display: {ex}")
    root.withdraw()
    return root


def test_editor_window_round_trip(tmp_path, monkeypatch):
    ads = tmp_path / "ads-list.json"
    ads_list.save(str(ads), ["first", "second"])
    root = _root()
    try:
        cfg = Config(auto_reply_enabled=False, auto_reply_file="ads-list.json")
        root.e = SimpleNamespace(
            cfg=cfg, cfg_path=str(tmp_path / "config.toml"), t=lambda k: tr("th", k)
        )
        root.px = lambda v: int(v)
        root.f_small = root.f_list = root.f_bold = root.f_icon = tkfont.Font(root, size=10)
        root._listbox = lambda parent: tk.Listbox(parent, exportselection=False)
        ed = AdsEditor(root)
        assert ed.lb.get(0, "end") == ("1. first", "2. second")
        assert ed._text().strip() == "first"  # first row selected and loaded
        ed._set_text("third ad")
        ed.add()
        ed.lb.selection_clear(0, "end")
        ed.lb.selection_set(0)
        ed.move(1)
        assert ed.draft.items == ["second", "first", "third ad"] and ed.draft.dirty
        assert ed.save()
        assert ads_list.load(str(ads)) == ["second", "first", "third ad"]
        ed.close()  # saved: closes without asking
        assert not ed.win.winfo_exists()
    finally:
        root.destroy()


def test_close_with_unsaved_changes_can_be_cancelled(tmp_path, monkeypatch):
    root = _root()
    try:
        root.e = SimpleNamespace(
            cfg=Config(auto_reply_file=str(tmp_path / "a.json")),
            cfg_path=None,
            t=lambda k: tr("en", k),
        )
        root.px = lambda v: int(v)
        root.f_small = root.f_list = root.f_bold = root.f_icon = tkfont.Font(root, size=10)
        root._listbox = lambda parent: tk.Listbox(parent, exportselection=False)
        ed = AdsEditor(root)
        ed._set_text("new")
        ed.add()
        import autodj.gui_ads as mod

        monkeypatch.setattr(mod.messagebox, "askyesnocancel", lambda *a, **k: None)
        ed.close()
        assert ed.win.winfo_exists()  # cancelled: still open
        monkeypatch.setattr(mod.messagebox, "askyesnocancel", lambda *a, **k: False)
        ed.close()
        assert not ed.win.winfo_exists()  # discarded
        assert ads_list.load(str(tmp_path / "a.json")) == []
    finally:
        root.destroy()


def test_every_editor_label_exists_in_both_languages():
    keys = [
        "g_ads_editor", "g_ads_editor_title", "g_ads_count", "g_ads_disabled_note",
        "g_ads_add", "g_ads_update", "g_ads_delete", "g_ads_up", "g_ads_down",
        "g_ads_save", "g_ads_close", "g_ads_unsaved", "g_ads_save_failed", "g_ads_too_long",
    ]  # fmt: skip
    for lang in ("en", "th"):
        for k in keys:
            assert tr(lang, k) != k, (lang, k)
