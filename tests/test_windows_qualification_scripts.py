"""Tests for Windows Qualification Kit PowerShell scripts.

These tests validate the structure and syntax of PowerShell scripts
without requiring a Windows execution environment.
"""

from pathlib import Path

import pytest

QUAL_DIR = Path(__file__).resolve().parent.parent / "tools" / "windows-qualification"
CAMELFROG_DIR = Path(__file__).resolve().parent.parent / "tools" / "camfrog-qualification"


def test_windows_qualification_directory_exists():
    """Windows qualification directory exists."""
    assert QUAL_DIR.is_dir(), f"Directory not found: {QUAL_DIR}"


def test_camfrog_qualification_directory_exists():
    """Camfrog qualification directory exists."""
    assert CAMELFROG_DIR.is_dir(), f"Directory not found: {CAMELFROG_DIR}"


def test_invoke_autodj_doctor_exists():
    """Invoke-AutoDJDoctor.ps1 exists."""
    script = QUAL_DIR / "Invoke-AutoDJDoctor.ps1"
    assert script.is_file(), f"Script not found: {script}"


def test_build_autodj_exists():
    """Build-AutoDJ.ps1 exists."""
    script = QUAL_DIR / "Build-AutoDJ.ps1"
    assert script.is_file(), f"Script not found: {script}"


def test_test_autodj_installer_exists():
    """Test-AutoDJInstaller.ps1 exists."""
    script = QUAL_DIR / "Test-AutoDJInstaller.ps1"
    assert script.is_file(), f"Script not found: {script}"


def test_test_autodj_runtime_exists():
    """Test-AutoDJRuntime.ps1 exists."""
    script = QUAL_DIR / "Test-AutoDJRuntime.ps1"
    assert script.is_file(), f"Script not found: {script}"


def test_collect_autodj_evidence_exists():
    """Collect-AutoDJEvidence.ps1 exists."""
    script = QUAL_DIR / "Collect-AutoDJEvidence.ps1"
    assert script.is_file(), f"Script not found: {script}"


def test_test_autodj_codesigning_exists():
    """Test-AutoDJCodeSigning.ps1 exists."""
    script = QUAL_DIR / "Test-AutoDJCodeSigning.ps1"
    assert script.is_file(), f"Script not found: {script}"


def test_camfrog_test_exists():
    """Test-AutoDJCamfrogIntegration.ps1 exists."""
    script = CAMELFROG_DIR / "Test-AutoDJCamfrogIntegration.ps1"
    assert script.is_file(), f"Script not found: {script}"


def test_powershell_scripts_have_balanced_braces():
    """PowerShell scripts have balanced curly braces (outside comment blocks)."""
    scripts = list(QUAL_DIR.glob("*.ps1")) + list(CAMELFROG_DIR.glob("*.ps1"))
    assert len(scripts) > 0, "No PowerShell scripts found"

    for script in scripts:
        content = script.read_text(encoding="utf-8")
        # Remove PowerShell comment blocks <# ... #> which may contain braces
        import re
        cleaned = re.sub(r"<#.*?#>", "", content, flags=re.DOTALL)
        # Remove single-quoted strings '...'
        cleaned = re.sub(r"'[^']*'", "''", cleaned)
        # Remove double-quoted strings "..."
        cleaned = re.sub(r'"[^"]*"', '""', cleaned)
        # Remove line comments
        lines = []
        for line in cleaned.split("\n"):
            if "#" in line:
                parts = line.split("#")
                quote_count = sum(1 for p in parts[: len(parts) - 1] for c in p if c == '"')
                if quote_count % 2 == 0:
                    line = "#".join(parts[: len(parts) - 1])
            lines.append(line)
        cleaned = "\n".join(lines)
        open_count = cleaned.count("{")
        close_count = cleaned.count("}")
        assert open_count == close_count, (
            f"{script.name}: Unbalanced braces ({open_count} open, {close_count} close)"
        )


def test_powershell_scripts_have_param_block():
    """PowerShell scripts have a param block."""
    scripts = list(QUAL_DIR.glob("*.ps1")) + list(CAMELFROG_DIR.glob("*.ps1"))
    for script in scripts:
        content = script.read_text(encoding="utf-8")
        assert "param(" in content, f"{script.name}: Missing param block"


def test_installer_test_has_safety_assertions():
    """Installer test harness includes user data safety assertions."""
    script = QUAL_DIR / "Test-AutoDJInstaller.ps1"
    content = script.read_text(encoding="utf-8")
    # Check for key safety assertions
    assert 'config.toml' in content, "Missing config.toml safety check"
    assert 'playlist.json' in content, "Missing playlist.json safety check"
    # The uninstaller must NOT contain RMDir "$INSTDIR" (that was the bug)
    assert 'RMDir "$INSTDIR"' not in content, (
        "Installer test should not contain RMDir $INSTDIR (that was the bug we fixed)"
    )


def test_runtime_test_has_simulated_marker():
    """Runtime test harness distinguishes simulated from live tests."""
    script = QUAL_DIR / "Test-AutoDJRuntime.ps1"
    content = script.read_text(encoding="utf-8")
    assert 'Simulated' in content, "Missing Simulated marker"
    assert 'NOT RUN' in content, "Missing NOT RUN status"


def test_codesigning_has_fail_closed():
    """Code signing test fails closed without certificate."""
    script = QUAL_DIR / "Test-AutoDJCodeSigning.ps1"
    content = script.read_text(encoding="utf-8")
    assert 'BLOCKED' in content, "Missing BLOCKED status for missing certificate"
    assert 'AUTODJ_PFX' in content, "Missing AUTODJ_PFX env var reference"
    assert 'AUTODJ_CERT_THUMBPRINT' in content, "Missing AUTODJ_CERT_THUMBPRINT env var reference"


def test_camfrog_test_has_live_marker():
    """Camfrog test distinguishes live from mock tests."""
    script = CAMELFROG_DIR / "Test-AutoDJCamfrogIntegration.ps1"
    content = script.read_text(encoding="utf-8")
    assert 'RunLive' in content, "Missing RunLive parameter"
    assert 'Live' in content, "Missing Live marker"


def test_collect_evidence_sanitizes_secrets():
    """Evidence collector sanitizes secrets."""
    script = QUAL_DIR / "Collect-AutoDJEvidence.ps1"
    content = script.read_text(encoding="utf-8")
    assert 'REDACTED' in content, "Missing secret redaction"
    assert 'Sanitize-Content' in content, "Missing Sanitize-Content function"


def test_docs_qualification_directory_exists():
    """docs/qualification directory exists."""
    docs_dir = Path(__file__).resolve().parent.parent / "docs" / "qualification"
    assert docs_dir.is_dir(), f"Directory not found: {docs_dir}"


def test_qualification_docs_exist():
    """Qualification documentation files exist."""
    docs_dir = Path(__file__).resolve().parent.parent / "docs" / "qualification"
    expected_files = [
        "WINDOWS_QUALIFICATION_GUIDE.md",
        "AUTHENTICODE_SETUP.md",
        "CAMFROG_LIVE_TESTING.md",
        "QUALIFICATION_EVIDENCE_SCHEMA.md",
    ]
    for fname in expected_files:
        assert (docs_dir / fname).is_file(), f"Missing doc: {fname}"