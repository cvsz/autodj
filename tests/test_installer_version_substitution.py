"""Installer version plumbing: every build path must render the real version.

The NSIS script defaults APP_VERSION via ``!define /IfNDef``.  A command-line
``/DAPP_VERSION=`` define overrides that default, and both installer scripts
also render a concrete copy of ``installer.nsi`` so a stale default can never
silently name an artifact with the wrong version.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RENDER = ROOT / "scripts" / "render_installer_nsi.py"
PS1 = ROOT / "scripts" / "build_installer.ps1"
SH = ROOT / "scripts" / "build_installer_linux.sh"
RELEASE = ROOT / ".github" / "workflows" / "release.yml"


def _render(tmp_path: Path, template: str, version: str = "0.3.0"):
    source = tmp_path / "installer.nsi"
    output = tmp_path / "rendered.nsi"
    source.write_text(template, encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(RENDER),
            "--version",
            version,
            "--input",
            str(source),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    return result, output


def test_render_replaces_ifndef_default(tmp_path):
    result, output = _render(
        tmp_path,
        '!define /IfNDef APP_VERSION "9.9.9"\nName "CamfrogAutoDJ ${APP_VERSION}"\n',
    )

    assert result.returncode == 0, result.stderr
    rendered = output.read_text(encoding="utf-8")
    assert '!define /IfNDef APP_VERSION "0.3.0"' in rendered
    assert "9.9.9" not in rendered


def test_render_replaces_plain_define(tmp_path):
    result, output = _render(tmp_path, '!define APP_VERSION "9.9.9"\nOutFile "x.exe"\n')

    assert result.returncode == 0, result.stderr
    rendered = output.read_text(encoding="utf-8")
    assert '!define APP_VERSION "0.3.0"' in rendered
    assert "9.9.9" not in rendered


def test_render_fails_loudly_when_define_is_missing(tmp_path):
    result, _ = _render(tmp_path, 'Name "no version here"\n')

    assert result.returncode != 0
    assert "APP_VERSION" in result.stderr


def test_installer_scripts_use_shared_renderer_and_app_version_define():
    ps1 = PS1.read_text(encoding="utf-8")
    sh = SH.read_text(encoding="utf-8")

    for script in (ps1, sh):
        assert "render_installer_nsi.py" in script
        assert "/DAPP_VERSION=" in script
        # The old, ignored define name must not survive.
        assert "/DVERSION=" not in script


def test_release_workflow_passes_app_version_without_tag_prefix():
    workflow = RELEASE.read_text(encoding="utf-8")

    assert "/DAPP_VERSION=" in workflow
    assert "/DVERSION=${{ github.ref_name }}" not in workflow
    # Tags are vX.Y.Z while pyproject/NSIS use X.Y.Z.
    assert "GITHUB_REF_NAME" in workflow
    assert "replace" in workflow
