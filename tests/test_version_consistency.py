"""Test that version is consistent across all artifacts."""

import re
from pathlib import Path


def test_version_consistency():
    """All version references should be 0.3.0."""
    # Read version from pyproject.toml
    pyproject = Path("pyproject.toml").read_text()
    pyproject_version = re.search(r'version = "([^"]+)"', pyproject).group(1)
    assert pyproject_version == "0.3.0", f"pyproject.toml: {pyproject_version}"

    # Read from __init__.py
    init = Path("camfrog_autodj/__init__.py").read_text()
    init_version = re.search(r'__version__ = "([^"]+)"', init).group(1)
    assert init_version == "0.3.0", f"__init__.py: {init_version}"

    # Read from version_info.txt
    version_info = Path("version_info.txt").read_text()
    version_info_match = re.search(
        r"filevers=\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", version_info
    )
    assert version_info_match, "version_info.txt missing filevers"
    version_info_version = (
        f"{version_info_match.group(1)}.{version_info_match.group(2)}.{version_info_match.group(3)}"
    )
    assert version_info_version == "0.3.0", f"version_info.txt: {version_info_version}"

    # Read from installer.nsi
    installer = Path("installer.nsi").read_text()
    installer_match = re.search(r'!define /IfNDef APP_VERSION "([^"]+)"', installer)
    assert installer_match, "installer.nsi missing APP_VERSION"
    installer_version = installer_match.group(1)
    assert installer_version == "0.3.0", f"installer.nsi: {installer_version}"

    # Read from install.bat
    install_bat = Path("install.bat").read_text()
    install_bat_match = re.search(r"Version ([\d.]+)", install_bat)
    assert install_bat_match, "install.bat missing version"
    install_bat_version = install_bat_match.group(1)
    assert install_bat_version == "0.3.0", f"install.bat: {install_bat_version}"

    # Read from install.ps1
    install_ps1 = Path("install.ps1").read_text()
    install_ps1_match = re.search(r"Version ([\d.]+)", install_ps1)
    assert install_ps1_match, "install.ps1 missing version"
    install_ps1_version = install_ps1_match.group(1)
    assert install_ps1_version == "0.3.0", f"install.ps1: {install_ps1_version}"
