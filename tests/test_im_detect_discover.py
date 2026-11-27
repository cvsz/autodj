"""Regression tests: IM detection only in a line's header; discover ignores empty windows.

Live (v0.3.10): the bot's own room reply "ขอเพลงผ่านข้อความส่วนตัว (IM) ได้เลยครับ"
was read back as an IM from the bot's account, and auto-discover saved Camfrog's
room list ("รายชื่อห้องสนทนา") as the room window while the room was closed.
"""

from __future__ import annotations

import re

import pytest

from autodj.adapters.base import compile_join_rx
from autodj.adapters.uia import UiaAdapter, _has_im_marker
from autodj.config import Config
from autodj.discover import Ctl, best_room, score_window

BOT_REPLY = "9:24 Seaza: ขอเพลงผ่านข้อความส่วนตัว (IM) ได้เลยครับ"


@pytest.mark.parametrize(
    "line",
    [
        BOT_REPLY,
        "Seaza: use [IM] to ask",
        "6:55 zdevz: send me an IM: please",
        "zdevz: (IM)",
        "9:24 alice: hi",
    ],
)
def test_marker_in_message_body_is_not_an_im(line):
    assert _has_im_marker(line) is False


@pytest.mark.parametrize(
    "line",
    [
        "IM zdevz: !play x",
        "[IM] zdevz: !play x",
        "(IM) zdevz: !play x",
        "PM zdevz: hi",
        "Private: zdevz: hi",
        "IM from zdevz: hi",
        "private message from zdevz: hi",
        "9:24 [IM] zdevz: !play x",
        "[9:24] (IM) zdevz: !play x",
        "9:24 zdevz (IM): !play x",
    ],
)
def test_marker_in_header_is_an_im(line):
    assert _has_im_marker(line) is True


def _adapter() -> UiaAdapter:
    cfg = Config()
    a = UiaAdapter.__new__(UiaAdapter)  # no Windows window needed for line parsing
    a.cfg = cfg
    a.rx = re.compile(cfg.line_regex)
    a.join_rx = compile_join_rx(cfg.join_line_regex)
    return a


def test_bot_room_reply_parses_as_room_line_not_im():
    m = _adapter()._room_line_message(BOT_REPLY)
    assert m is not None
    assert m.user == "Seaza"
    assert m.is_im is False


def test_real_im_line_still_parses_as_im():
    m = _adapter()._room_line_message("9:24 [IM] zdevz: !play song")
    assert m is not None and m.is_im is True and m.user == "zdevz"


# ---- discover -------------------------------------------------------------------------------


def test_room_list_window_is_not_a_room():
    """Room list = Document (list) + Edit (search box), no chat lines."""
    rx = re.compile(Config().line_regex)
    ctls = [
        Ctl("Document", 0, "ZeaZDev\nMusic Lovers\nThai Chat\n", 0, 0, 600, 500),
        Ctl("Edit", 0, "", 0, 520, 600, 550),
    ]
    assert score_window("รายชื่อห้องสนทนา", ctls, rx) is None


def test_empty_candidates_leave_config_unchanged():
    rx = re.compile(Config().line_regex)
    room_list = score_window(
        "รายชื่อห้องสนทนา",
        [Ctl("Document", 0, "", 0, 0, 600, 500), Ctl("Edit", 0, "", 0, 520, 600, 550)],
        rx,
    )
    assert best_room([f for f in (room_list,) if f]) is None


def test_window_with_chat_lines_is_still_a_room():
    rx = re.compile(Config().line_regex)
    ctls = [
        Ctl("Document", 0, "alice: hi\nbob: yo\n", 0, 0, 600, 500),
        Ctl("Edit", 0, "", 0, 520, 600, 550),
    ]
    f = score_window("ZeaZDev", ctls, rx)
    assert f is not None and f.matched == 2


# ---- installer packaging (CI "Build NSIS installer") -----------------------------------------

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent


def test_installer_name_matches_build_script_and_workflows():
    """installer.nsi once wrote AutoDJ-Setup-<v>.exe while every consumer looked for
    zAutoDJ-Setup-<v>.exe ("Installer not found after build")."""
    nsi = (ROOT / "installer.nsi").read_text(encoding="utf-8")
    m = re.search(r'!define /IfNDef INSTALLER_NAME "([^"]+)"', nsi)
    assert m is not None
    assert m.group(1) == "zAutoDJ-Setup-${APP_VERSION}.exe"
    script = (ROOT / "scripts" / "build_installer.ps1").read_text(encoding="utf-8")
    assert '"zAutoDJ-Setup-$Version.exe"' in script
    wf = (ROOT / ".github" / "workflows" / "windows-build.yml").read_text(encoding="utf-8")
    assert "zAutoDJ-Setup-" in wf


def test_build_installer_stages_every_dist_file_the_nsi_packages():
    """installer.nsi packages dist\\start.bat, check.bat and readme.txt; the build script
    (not only `make portable`) must create them or makensis aborts."""
    script = (ROOT / "scripts" / "build_installer.ps1").read_text(encoding="utf-8")
    assert '"dist-readme.txt"     = "readme.txt"' in script
    assert "tools\\make_client_shortcuts.py $SrcDir" in script
    assert (ROOT / "dist-readme.txt").is_file()


def test_make_client_shortcuts_writes_launchers(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "make_client_shortcuts", ROOT / "tools" / "make_client_shortcuts.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    (tmp_path / "zAutoDJ.exe").write_bytes(b"")
    mod.main([str(tmp_path)])
    start = (tmp_path / "start.bat").read_text(encoding="utf-8")
    assert '"zAutoDJ.exe" --gui' in start
    assert '"zAutoDJ.exe" --check' in (tmp_path / "check.bat").read_text(encoding="utf-8")
