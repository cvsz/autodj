from pathlib import Path


def test_installer_preserves_existing_user_config_on_upgrade():
    root = Path(__file__).resolve().parent.parent
    script = (root / "installer.nsi").read_text(encoding="utf-8")

    assert 'IfFileExists "$INSTDIR\\config.toml" config_exists' in script
    assert "File /oname=config.toml config.example.toml" in script


def test_uninstaller_removes_only_application_owned_files():
    root = Path(__file__).resolve().parent.parent
    script = (root / "installer.nsi").read_text(encoding="utf-8")
    uninstall = script.split("Section Uninstall", 1)[1].split("SectionEnd", 1)[0]

    assert 'RMDir /r "$INSTDIR"' not in uninstall
    assert 'RMDir "$INSTDIR"' not in uninstall, (
        "Uninstaller must not delete $INSTDIR itself — user data may remain"
    )
    assert 'Delete "$INSTDIR\\AutoDJ.exe"' in uninstall
    assert 'Delete "$INSTDIR\\config.toml"' not in uninstall, (
        "Uninstaller must not delete user config.toml"
    )
    assert 'Delete "$INSTDIR\\playlist.json"' not in uninstall, (
        "Uninstaller must not delete user playlist.json"
    )
    assert "Keep config.toml, playlist.json, logs, playlists" in uninstall
