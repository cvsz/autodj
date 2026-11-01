from pathlib import Path
import tomllib
import camfrog_autodj


def test_version_consistency():
    version = camfrog_autodj.__version__
    assert version == "0.2.6"

    # pyproject.toml
    root = Path(__file__).resolve().parent.parent
    pyproject = root / "pyproject.toml"
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)
    assert data["project"]["version"] == version

    # installer.nsi
    installer_nsi = (root / "installer.nsi").read_text(encoding="utf-8")
    assert f'!define APP_VERSION "{version}"' in installer_nsi

    # version_info.txt
    version_info = (root / "version_info.txt").read_text(encoding="utf-8")
    assert "filevers=(0, 2, 6, 0)" in version_info
    assert "prodvers=(0, 2, 6, 0)" in version_info
    assert "FileVersion', '0.2.6.0'" in version_info
    assert "ProductVersion', '0.2.6.0'" in version_info

    # install scripts
    install_bat = (root / "install.bat").read_text(encoding="utf-8")
    assert f"Version {version}" in install_bat

    install_ps1 = (root / "install.ps1").read_text(encoding="utf-8")
    assert f"Version {version}" in install_ps1

    # build installer scripts
    build_installer_ps1 = (root / "scripts" / "build_installer.ps1").read_text(encoding="utf-8")
    assert f'[string]$Version = "{version}"' in build_installer_ps1

    build_installer_linux = (root / "scripts" / "build_installer_linux.sh").read_text(encoding="utf-8")
    assert f'VERSION="${{1:-{version}}}"' in build_installer_linux

    # release workflow targets
    release_yml = (root / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "dist/AutoDJ.exe" in release_yml
    assert "Camfrog-AutoDJ-Setup-*.exe" in release_yml
    assert "SHA256SUMS.txt" in release_yml
    assert "actions/upload-artifact@v4" in release_yml
