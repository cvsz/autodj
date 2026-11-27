"""tools/migrate_to_zautodj.ps1 moves an old AutoDJ install over to zAutoDJ (0.4.0).

Runs the sandbox script tests/windows/migrate_to_zautodj_check.ps1 (temp folder +
HKCU:\\Software\\zautodj-migrate-test, both removed): shortcuts to the old exe are
re-pointed, old uninstall / App Paths / Software\\AutoDJ entries for that folder go,
the old exe is deleted, and nothing outside the install folder is touched.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "migrate_to_zautodj.ps1"
CHECK = ROOT / "tests" / "windows" / "migrate_to_zautodj_check.ps1"


def test_installer_runs_the_migration():
    nsi = (ROOT / "installer.nsi").read_text(encoding="utf-8")
    assert "migrate_to_zautodj.ps1" in nsi
    assert 'File "dist\\zAutoDJ.exe"' in nsi
    assert '"Software\\zAutoDJ"' in nsi


@pytest.mark.skipif(os.name != "nt" or not shutil.which("powershell"), reason="Windows only")
def test_migration_sandbox():
    out = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(CHECK),
            "-MigrateScript",
            str(SCRIPT),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    text = out.stdout + out.stderr
    assert "ALL=True" in text, text
    assert "FAIL" not in text, text
    assert "registry test key exists=False temp exists=False" in text, text
