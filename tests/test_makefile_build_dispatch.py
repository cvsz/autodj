"""`make build*` must work on Linux and on Windows 11.

The Makefile dispatches on ``$(OS)``.  These tests keep the Windows recipes
unchanged and require the Linux recipes to delegate to the Wine builder
instead of failing with "requires Windows".
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = ROOT / "Makefile"


def _block(target: str) -> str:
    text = MAKEFILE.read_text(encoding="utf-8")
    match = re.search(
        rf"(?ms)^{re.escape(target)}:.*?(?=^[A-Za-z0-9_.-]+:|\Z)",
        text,
    )
    assert match, f"target {target} not found"
    return match.group(0)


def _linux_dry_run(target: str) -> str:
    env = {key: value for key, value in os.environ.items() if key != "OS"}
    result = subprocess.run(
        ["make", "-n", target],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_build_dispatches_to_wine_builder_on_linux():
    block = _block("build")

    assert "build.ps1" in block  # Windows branch stays
    assert "scripts/build_exe_linux.sh" in block
    assert "build requires Windows" not in block

    dry_run = _linux_dry_run("build")
    assert "scripts/build_exe_linux.sh" in dry_run
    assert "build requires Windows" not in dry_run


def test_build_clean_dispatches_to_wine_builder_on_linux():
    block = _block("build-clean")

    assert "build.ps1 -Clean" in block
    assert "scripts/build_exe_linux.sh" in block
    assert "--clean" in block
    assert "build-clean requires Windows" not in block

    dry_run = _linux_dry_run("build-clean")
    assert "scripts/build_exe_linux.sh" in dry_run


def test_build_all_dispatches_to_exe_then_installer_on_linux():
    block = _block("build-all")

    assert "build.ps1" in block  # Windows branch stays
    assert "scripts/build_exe_linux.sh" in block
    assert "scripts/build_installer_linux.sh" in block
    assert "build-all requires Windows" not in block

    dry_run = _linux_dry_run("build-all")
    assert "scripts/build_exe_linux.sh" in dry_run
    assert "scripts/build_installer_linux.sh" in dry_run


def test_build_all_linux_is_an_alias_not_a_second_pipeline():
    block = _block("build-all-linux")

    assert "$(MAKE) build-all" in block
    assert "wine64" not in block
    assert "makensis.exe" not in block


def test_help_says_build_targets_are_cross_platform():
    help_text = _block("help")

    assert "both platforms" in help_text.lower() or "Linux" in help_text
