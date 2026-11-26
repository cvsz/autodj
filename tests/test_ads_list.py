"""ads-list.json load/save (GUI ads editor) and the auto-reply loop picking up edits."""

from __future__ import annotations

import json
import os

import pytest
from test_core import FakeAdapter, FakePlayer, out

from autodj import ads_list
from autodj.config import Config
from autodj.engine import Engine


def test_load_accepts_every_known_format(tmp_path):
    p = tmp_path / "a.json"
    for data in (
        {"version": 1, "messages": ["a", " b ", "", None]},
        ["a", "b"],
        {"ads": ["a", "b"]},
    ):
        p.write_text(json.dumps(data), "utf-8")
        assert ads_list.load(str(p)) == ["a", "b"]


def test_load_missing_or_broken_file_is_empty(tmp_path):
    assert ads_list.load(str(tmp_path / "none.json")) == []
    bad = tmp_path / "bad.json"
    bad.write_text("{ nope", "utf-8")
    assert ads_list.load(str(bad)) == []


def test_save_writes_canonical_utf8_and_keeps_a_backup(tmp_path):
    p = tmp_path / "ads-list.json"
    p.write_text(json.dumps(["old"]), "utf-8")
    written = ads_list.save(str(p), ["  ขอเพลงผ่าน IM ได้เลย  ", "", "second"])
    assert written == ["ขอเพลงผ่าน IM ได้เลย", "second"]
    data = json.loads(p.read_text("utf-8"))
    assert data == {"version": 1, "messages": written}
    assert "ขอเพลง" in p.read_text("utf-8")  # not \\u escaped: readable by hand
    assert json.loads((tmp_path / "ads-list.json.bak").read_text("utf-8")) == ["old"]
    assert [f for f in os.listdir(tmp_path) if f.endswith(".tmp")] == []


def test_save_rejects_bad_input_and_leaves_the_file(tmp_path):
    p = tmp_path / "ads-list.json"
    p.write_text(json.dumps(["keep"]), "utf-8")
    with pytest.raises(ValueError):
        ads_list.save(str(p), ["x" * (ads_list.MAX_AD_CHARS + 1)])
    with pytest.raises(ValueError):
        ads_list.save(str(p), ["x"] * (ads_list.MAX_ADS + 1))
    assert ads_list.load(str(p)) == ["keep"]


def test_resolve_path_is_relative_to_the_config_folder(tmp_path):
    cfg = str(tmp_path / "config.toml")
    assert ads_list.resolve_path("ads-list.json", cfg) == str(tmp_path / "ads-list.json")
    assert ads_list.resolve_path(str(tmp_path / "x.json"), cfg) == str(tmp_path / "x.json")


class _Ticks:
    def __init__(self, n, on_tick=None):
        self.n, self.on_tick, self.calls = n, on_tick, 0

    def wait(self, _timeout=None):
        self.calls += 1
        if self.on_tick:
            self.on_tick(self.calls)
        return self.calls > self.n

    def is_set(self):
        return self.calls > self.n


def test_loop_waits_for_an_empty_file_and_reloads_after_an_edit(tmp_path):
    ads = tmp_path / "ads-list.json"
    cfg = Config(auto_reply_enabled=True, auto_reply_interval=60.0, auto_reply_file=str(ads))
    e = Engine(cfg, FakeAdapter(), player=FakePlayer(), index=None)

    def edit(call):
        if call == 1:  # the operator saves the list in the GUI while the loop waits
            ads_list.save(str(ads), ["new ad"])

    e.stop_evt = _Ticks(2, edit)
    e._auto_reply_loop()
    assert out(e) == ["new ad"]
