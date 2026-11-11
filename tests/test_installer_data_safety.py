from pathlib import Path


def test_installer_preserves_existing_user_config_on_upgrade():
    root = Path(__file__).resolve().parent.parent
    script = (root / "installer.nsi").read_text(encoding="utf-8")

    config_check = 'IfFileExists "$INSTDIR\\config.toml" config_exists'
    config_template = 'File "dist\\config.toml"'

    assert config_check in script
    assert config_template in script

    # Verify that the existence check precedes default config installation.
    config_check_position = script.index(config_check)
    template_position = script.index(config_template)
    skip_label_position = script.index("config_exists:", template_position)

    assert config_check_position < template_position < skip_label_position


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
