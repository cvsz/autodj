"""The release exe must bundle the same optional features as the CI Windows build.

PyInstaller freezes only installed packages. release.yml's build job installed
``-e .`` without extras, so the published v0.3.13 AutoDJ.exe had no watchdog (config
hot reload disabled at startup) and no webhook server dependencies, while the
windows-build.yml build had both.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"


def _build_job(text: str) -> str:
    start = text.index("build-installer:")
    return text[start:]


def _install_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if "pip install -e" in line]


def _extras(line: str) -> set[str]:
    m = re.search(r"-e\s+\"?\.\[([^\]]*)\]", line)
    return set(m.group(1).split(",")) if m else set()


def test_release_build_installs_hotreload_and_webhook_extras():
    lines = _install_lines(_build_job((WORKFLOWS / "release.yml").read_text(encoding="utf-8")))
    assert lines, "release.yml build-installer installs the package"
    assert {"hotreload", "webhook"} <= _extras(lines[0]), lines[0]


def test_release_build_extras_cover_the_ci_windows_build():
    ci = _install_lines((WORKFLOWS / "windows-build.yml").read_text(encoding="utf-8"))
    rel = _install_lines(_build_job((WORKFLOWS / "release.yml").read_text(encoding="utf-8")))
    runtime = _extras(ci[0]) - {"dev", "build"}  # test/build-only extras
    assert runtime <= _extras(rel[0]), (ci[0], rel[0])
