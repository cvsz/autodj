"""Release signing scripts must run under Windows PowerShell 5.1.

release.yml runs build.ps1 and tools/sign_exe.ps1 with ``powershell.exe`` (5.1).
``Get-PfxCertificate -Password`` exists only in PowerShell 7+, so the v0.3.12 release
run failed at "Sign NSIS installer" before anything was published.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIGN_EXE = ROOT / "tools" / "sign_exe.ps1"
BUILD = ROOT / "build.ps1"
RELEASE = ROOT / ".github" / "workflows" / "release.yml"


def _code(path: Path) -> str:
    """Script text without comment lines (comments may name the old cmdlet)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(line for line in lines if not line.lstrip().startswith("#"))


def test_pfx_loading_does_not_need_powershell_7():
    for script in (SIGN_EXE, BUILD):
        code = _code(script)
        assert not re.search(r"Get-PfxCertificate\b[^\n]*-Password", code), script.name
        assert "X509Certificate2(" in code, script.name


def test_release_runs_sign_exe_with_windows_powershell():
    # The assumption the test above protects: the signing script runs under 5.1.
    assert "powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\\sign_exe.ps1" in (
        RELEASE.read_text(encoding="utf-8")
    )
