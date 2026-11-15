"""CLI contract of scripts/build_exe_linux.sh.

The Makefile calls this script as ``build_exe_linux.sh <version>`` and
``build_exe_linux.sh <version> --clean``.  It must accept both, clean the
generated spec like ``build.ps1 -Clean``, and fail with actionable hints when
Wine or the Windows Python is unusable.
"""

from __future__ import annotations

import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "build_exe_linux.sh"


def _fake_wine(tmp_path: Path) -> Path:
    path = tmp_path / "wine"
    path.write_text(
        '#!/bin/sh\nif [ "$1" = "--version" ]; then echo "fake-wine 1.0"; exit 0; fi\nexit 1\n',
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def test_accepts_version_and_clean_arguments():
    script = SCRIPT.read_text(encoding="utf-8")

    assert "--clean" in script
    assert "CLEAN=1" in script
    assert "POSITIONAL" in script


def test_clean_also_removes_the_generated_spec():
    script = SCRIPT.read_text(encoding="utf-8")

    assert "rm -rf build dist AutoDJ.spec" in script


def test_wine_binary_can_be_overridden_for_tests():
    script = SCRIPT.read_text(encoding="utf-8")

    assert 'WINE_BIN="${WINE_BIN:-' in script


def test_missing_pyinstaller_fails_with_actionable_hint():
    """Build script must give an actionable hint when PyInstaller is missing."""
    script = SCRIPT.read_text(encoding="utf-8")
    # Script must check for PyInstaller and exit with actionable hint
    assert "PyInstaller --version" in script
    assert "PyInstaller is not installed" in script
    assert "pip install pyinstaller" in script
    # Script must reference WINE_PYTHON for guidance
    assert "WINE_PYTHON" in script
