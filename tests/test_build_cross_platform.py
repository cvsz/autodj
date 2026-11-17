"""Cross-platform build plumbing: `make build*` on Linux/Wine + one PyInstaller flag source.

- ``tools/generate_spec.py`` is the single source of PyInstaller options; it
  regenerates ``AutoDJ.spec``, which ``build.ps1`` (Windows) and
  ``scripts/build_exe_linux.sh`` (Wine) both consume before every build.
- ``scripts/build_exe_linux.sh`` builds the same Windows exe under Wine and
  fails with actionable hints when the environment is incomplete (no wine,
  no Windows Python in the prefix, no PyInstaller).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "tools" / "generate_spec.py"
LINUX = ROOT / "scripts" / "build_exe_linux.sh"
PS1 = ROOT / "build.ps1"


def _gen_spec(tmp_path: Path, name: str = "AutoDJ") -> str:
    out = tmp_path / "AutoDJ.spec"
    result = subprocess.run(
        [sys.executable, str(GEN), "--name", name, "--output", str(out)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return out.read_text(encoding="utf-8")


class TestGenerateSpec:
    def test_spec_contains_shared_pyinstaller_flags(self, tmp_path):
        spec = _gen_spec(tmp_path)
        for token in [
            '"run_autodj.py"',
            '"app.ico"',
            '"version_info.txt"',
            'collect_all("yt_dlp")',
            'collect_submodules("camfrog_autodj")',
            'collect_submodules("pywinauto")',
            'collect_submodules("pyttsx3")',
            '"comtypes"',
            '"pyperclip"',
            '"mutagen"',
            "console=False",
            "upx=False",
        ]:
            assert token in spec, f"missing {token} in generated spec"

    def test_spec_is_onefile(self, tmp_path):
        spec = _gen_spec(tmp_path)
        assert "COLLECT(" not in spec  # onefile: binaries+datas go into EXE
        assert "a.binaries" in spec
        assert "a.datas" in spec

    def test_spec_name_follows_name_flag(self, tmp_path):
        spec = _gen_spec(tmp_path, name="AutoDJ")
        assert "name='AutoDJ'" in spec

    def test_spec_marks_itself_generated(self, tmp_path):
        spec = _gen_spec(tmp_path)
        assert "GENERATED" in spec
        assert "tools/generate_spec.py" in spec


class TestLinuxExeBuilder:
    def test_script_exists_and_parses(self):
        assert LINUX.exists(), f"missing {LINUX}"

        if os.name == "nt":
            pytest.skip("Linux shell syntax validation runs in Linux CI")

        bash = shutil.which("bash")
        if bash is None:
            pytest.skip("Bash is unavailable on this runner")

        subprocess.run([bash, "-n", str(LINUX)], check=True)

    def test_script_content_guards(self):
        script = LINUX.read_text(encoding="utf-8")
        for token in [
            "wine64",  # accepts wine OR wine64
            "WINE_PYTHON",  # interpreter override
            "AUTODJ_SKIP_SMOKE",  # smoke-test escape hatch
            "generate_spec.py",  # shared spec source
            "dist/AutoDJ.exe",
            "UNSIGNED",  # artifact must be labelled unsigned
            "check_build_env.py",  # mirrors build.ps1 env verification
            "dist/config.toml",  # mirrors build.ps1 post-build copies
        ]:
            assert token in script, f"missing {token}"

    def test_failure_messages_carry_install_hints(self):
        script = LINUX.read_text(encoding="utf-8")
        assert "apt install wine" in script
        assert "pip install pyinstaller" in script


class TestBuildPs1UsesSharedSpec:
    def test_build_ps1_regenerates_and_builds_from_spec(self):
        ps1 = PS1.read_text(encoding="utf-8")
        assert "generate_spec.py" in ps1
        assert "$Name.spec" in ps1  # PyInstaller input is the generated spec

    def test_build_ps1_no_longer_inlines_flags(self):
        ps1 = PS1.read_text(encoding="utf-8")
        for gone in [
            "--collect-all",
            "--collect-submodules",
            "--hidden-import",
            "--onefile",
            "--windowed",
            "--noupx",
        ]:
            assert gone not in ps1, f"stale inline flag {gone} must live in the generator"


INSTALLER_SH = ROOT / "scripts" / "build_installer_linux.sh"


class TestLinuxInstallerBuilder:
    """scripts/build_installer_linux.sh: native makensis first, correct file list,
    compile from the repo root so the nsi's dist\\... paths resolve."""

    def test_required_files_match_repo_and_installer(self):
        script = INSTALLER_SH.read_text(encoding="utf-8")
        assert '"LICENSE"' in script
        assert "LICENSE.md" not in script  # repo ships LICENSE, not LICENSE.md
        assert "uninstall.ps1" not in script  # NSIS generates the uninstaller

    def test_makensis_detection_prefers_native_then_wine(self):
        script = INSTALLER_SH.read_text(encoding="utf-8")
        assert "command -v makensis" in script  # tier 1: native on PATH
        assert "NSIS_PATH" in script  # tier 2: Windows makensis.exe in the prefix

    def test_compiles_from_repo_root_with_nocd(self):
        script = INSTALLER_SH.read_text(encoding="utf-8")
        assert "-NOCD" in script
        assert "REPO_ROOT" in script
        # the old script cd'd into SRCDIR, breaking the nsi's dist\\ relative paths
        assert re.search(r'cd "\$SRCDIR"', script) is None

    def test_default_version_derives_from_pyproject(self):
        script = INSTALLER_SH.read_text(encoding="utf-8")
        assert "tomllib" in script  # default comes from pyproject, never a literal
        assert "pyproject.toml" in script
        for stale in ["${1:-0.3.0}", "${1:-0.2.3}"]:
            assert stale not in script, f"hard-coded default version {stale}"
