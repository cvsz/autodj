"""CLI contract of scripts/build_exe_linux.sh.

The Makefile calls this script as ``build_exe_linux.sh <version>`` and
``build_exe_linux.sh <version> --clean``.  It must accept both, clean the
generated spec like ``build.ps1 -Clean``, and fail with actionable hints when
Wine or the Windows Python is unusable.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

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

    assert "rm -rf build dist zAutoDJ.spec" in script


def test_wine_binary_can_be_overridden_for_tests():
    script = SCRIPT.read_text(encoding="utf-8")

    assert 'WINE_BIN="${WINE_BIN:-' in script


def test_missing_pyinstaller_fails_with_actionable_hint(tmp_path):
    from conftest import posix_bash

    bash = posix_bash()
    if bash is None:
        pytest.skip("Bash is unavailable on this runner")

    windows_python = tmp_path / "python.exe"
    windows_python.write_bytes(b"not really python")

    env = dict(os.environ)
    # Git Bash needs forward-slash paths for WINE_BIN / WINE_PYTHON.
    env["WINE_BIN"] = _fake_wine(tmp_path).as_posix()
    env["WINE_PYTHON"] = windows_python.as_posix()

    result = subprocess.run(
        [bash, str(SCRIPT), "0.3.6"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "WINE_PYTHON" in output
    assert "pip install pyinstaller" in output
