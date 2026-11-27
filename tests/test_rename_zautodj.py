"""zAutoDJ rename (0.4.0): old installs, configs and updaters keep working."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from autodj import __main__ as main_mod
from autodj import paths
from autodj.updater import Updater

ROOT = Path(__file__).resolve().parent.parent


def test_user_app_dir_new_install(tmp_path):
    assert paths.user_app_dir(tmp_path) == tmp_path / "zAutoDJ"


def test_user_app_dir_keeps_a_relocated_config_from_before(tmp_path):
    old = tmp_path / "Camfrog AutoDJ"
    old.mkdir()
    (old / "config.toml").write_text("room = 'x'\n", encoding="utf-8")
    assert paths.user_app_dir(tmp_path) == old  # the CLI used this folder
    gui_old = tmp_path / "AutoDJ"
    gui_old.mkdir()
    (gui_old / "config.toml").write_text("room = 'y'\n", encoding="utf-8")
    assert paths.user_app_dir(tmp_path) == gui_old  # newest-first: the GUI's folder wins


def test_user_app_dir_ignores_legacy_folder_without_config(tmp_path):
    (tmp_path / "AutoDJ" / "comtypes_gen").mkdir(parents=True)  # cache only
    assert paths.user_app_dir(tmp_path) == tmp_path / "zAutoDJ"


def test_user_app_dir_prefers_existing_new_folder(tmp_path):
    (tmp_path / "zAutoDJ").mkdir()
    old = tmp_path / "AutoDJ"
    old.mkdir()
    (old / "config.toml").write_text("", encoding="utf-8")
    assert paths.user_app_dir(tmp_path) == tmp_path / "zAutoDJ"


def test_pre_rename_updater_config_still_finds_the_new_exe():
    """0.3.x configs say auto_update_asset = "AutoDJ.exe"; the release asset is zAutoDJ.exe."""
    cfg = SimpleNamespace(
        auto_update_enabled=True, auto_update_repo="cvsz/autodj", auto_update_asset="AutoDJ.exe"
    )
    up = Updater(cfg)
    up._latest = {
        "assets": [
            {"name": "zAutoDJ-Setup-0.4.0.exe"},
            {"name": "zAutoDJ-Full-v0.4.0.zip"},
            {"name": "SHA256SUMS.txt"},
            {"name": "zAutoDJ.exe"},
        ]
    }
    assert up.find_asset()["name"] == "zAutoDJ.exe"


def test_default_update_asset_is_the_new_exe():
    from autodj.config import Config

    assert Config().auto_update_asset == "zAutoDJ.exe"


def test_single_instance_claims_old_and_new_mutex_names(monkeypatch, tmp_path):
    seen: list[str] = []

    def fake(name):
        seen.append(name)
        return object(), False

    monkeypatch.setattr(main_mod, "_create_mutex", fake)
    assert main_mod._single_instance(str(tmp_path / "config.toml"))
    assert [n.split("-")[0] for n in seen] == ["Local\\zAutoDJ", "Local\\CamfrogAutoDJ"]
    assert seen[0].split("-", 1)[1] == seen[1].split("-", 1)[1]  # same config digest


def test_single_instance_refuses_when_an_old_exe_holds_the_config(monkeypatch, tmp_path):
    monkeypatch.setattr(
        main_mod, "_create_mutex", lambda name: (object(), name.startswith("Local\\CamfrogAutoDJ"))
    )
    monkeypatch.setattr(main_mod, "_show_already_running", lambda: None)
    assert not main_mod._single_instance(str(tmp_path / "config.toml"))


def test_generated_spec_follows_the_exe_name(tmp_path, monkeypatch):
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        import generate_spec
    finally:
        sys.path.pop(0)
    monkeypatch.chdir(tmp_path)
    assert generate_spec.main(["--name", "zAutoDJ"]) == 0
    assert "name='zAutoDJ'" in (tmp_path / "zAutoDJ.spec").read_text(encoding="utf-8")


def test_installer_names():
    nsi = (ROOT / "installer.nsi").read_text(encoding="utf-8")
    assert '!define /IfNDef APP_NAME "zAutoDJ"' in nsi
    assert 'InstallDir "$APPDATA\\zAutoDJ"' in nsi
    assert 'CreateShortcut "$SMPROGRAMS\\zAutoDJ\\zAutoDJ.lnk"' in nsi
    assert 'CreateShortcut "$DESKTOP\\zAutoDJ.lnk"' in nsi
    assert 'Uninstall\\zAutoDJ" "DisplayName" "${APP_NAME}"' in nsi
    # an upgrade keeps the pre-0.4.0 folder
    assert 'ReadRegStr $0 HKCU "Software\\AutoDJ" "InstallDir"' in nsi
    version_info = (ROOT / "version_info.txt").read_text(encoding="utf-8")
    assert "StringStruct('OriginalFilename', 'zAutoDJ.exe')" in version_info
    assert "StringStruct('ProductName', 'zAutoDJ')" in version_info
