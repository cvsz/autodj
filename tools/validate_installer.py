#!/usr/bin/env python3
"""Validate installer.nsi structure and required files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Files that must exist for the installer to build successfully
REQUIRED_FILES = [
    "dist/AutoDJ.exe",
    "app.ico",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    "run_autodj.py",
    "config.example.toml",
    "ads-list.json",
    "install.ps1",
    "install.bat",
]

# Directories that must exist
REQUIRED_DIRS = [
    "dist/mpv",
    "mpv/_internal",
    "mpv/vbcable",
    "docs",
    "tools",
    "playlist",
]

# Sections that must be present in installer.nsi
REQUIRED_SECTIONS = [
    "SEC_MAIN",
    "SEC_MPV",
    "SEC_VBCABLE",
    "SEC_PLAYLIST",
    "SEC_DOCS",
    "SEC_TOOLS",
    "SEC_SCRIPTS",
]

# Critical macros/commands that must be present
REQUIRED_COMMANDS = [
    'File "dist\\AutoDJ.exe"',
    'File "dist\\app.ico"',
    'File "dist\\ads-list.json"',
    'File "config.toml"',
    'File /r "dist\\playlist\\*.json"',
    "ExecWait",
    "mpv-register.bat",
    "WriteUninstaller",
    "CreateShortcut",
    "WriteRegStr",
    "DeleteRegKey",
    "Section Uninstall",
]

# NSIS script validation patterns
SECTION_PATTERN = re.compile(r'^\s*Section\s+(?:/o\s+)?".*?"\s+(\w+)', re.MULTILINE)
FUNCTION_PATTERN = re.compile(r"^\s*Function\s+(\w+)", re.MULTILINE)


def validate_required_files() -> list[str]:
    """Check that all required source files exist."""
    errors: list[str] = []
    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            errors.append(f"missing required file: {rel}")
    return errors


def validate_required_dirs() -> list[str]:
    """Check that all required directories exist."""
    errors: list[str] = []
    for rel in REQUIRED_DIRS:
        if not (ROOT / rel).exists():
            errors.append(f"missing required directory: {rel}")
    return errors


def _check_sections(content: str) -> list[str]:
    errors: list[str] = []
    sections = SECTION_PATTERN.findall(content)
    for req in REQUIRED_SECTIONS:
        if req not in sections:
            errors.append(f"missing required section: {req}")
    return errors


def _check_commands(content: str) -> list[str]:
    errors: list[str] = []
    for cmd in REQUIRED_COMMANDS:
        if cmd not in content:
            errors.append(f"missing required command in installer.nsi: {cmd}")
    return errors


def _check_common_patterns(content: str) -> list[str]:
    errors: list[str] = []
    if "RequestExecutionLevel user" not in content:
        errors.append("missing RequestExecutionLevel user")
    if 'InstallDir "$APPDATA' not in content:
        errors.append("missing APPDATA install directory")
    if "mpv-register.bat" not in content:
        errors.append("mpv-register.bat not executed in installer")
    return errors


def _check_uninstaller(content: str) -> list[str]:
    errors: list[str] = []
    uninstall_section = content.split("Section Uninstall", 1)
    if len(uninstall_section) > 1:
        uninstall_content = uninstall_section[1].split("SectionEnd", 1)[0]
        if 'Delete "$INSTDIR\\config.toml"' in uninstall_content:
            errors.append("uninstaller deletes config.toml (must preserve user data)")
        if 'Delete "$INSTDIR\\playlist.json"' in uninstall_content:
            errors.append("uninstaller deletes playlist.json (must preserve user data)")
        if "Keep config.toml, playlist.json, logs, playlists" not in uninstall_content:
            errors.append("uninstaller missing comment about preserving user data")
    return errors


def validate_installer_nsi() -> list[str]:
    """Validate installer.nsi structure and content."""
    errors: list[str] = []
    nsi_path = ROOT / "installer.nsi"
    if not nsi_path.exists():
        return ["installer.nsi not found"]

    content = nsi_path.read_text(encoding="utf-8")

    errors.extend(_check_sections(content))
    errors.extend(_check_commands(content))
    errors.extend(_check_common_patterns(content))
    errors.extend(_check_uninstaller(content))

    return errors


def validate_version_consistency() -> list[str]:
    """Check version consistency between installer.nsi and pyproject.toml."""
    errors: list[str] = []

    # Get version from pyproject.toml
    import tomllib

    try:
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        pyproject_version = pyproject.get("project", {}).get("version", "unknown")
    except Exception as e:
        return [f"could not read pyproject.toml version: {e}"]

    # Get version from installer.nsi
    nsi_path = ROOT / "installer.nsi"
    if nsi_path.exists():
        content = nsi_path.read_text(encoding="utf-8")
        # Look for APP_VERSION define
        match = re.search(r'!define\s+/IfNDef\s+APP_VERSION\s+"([^"]+)"', content)
        if match:
            nsi_version = match.group(1)
            if nsi_version != pyproject_version:
                errors.append(
                    f"version mismatch: pyproject.toml={pyproject_version}, installer.nsi={nsi_version}"
                )

    return errors


def main() -> int:
    # Cross-platform: installer.nsi validation is a Windows NSIS build gate.
    # Skip gracefully on non-Windows hosts so `make all` / `make validate-all`
    # work everywhere (Windows primary, Linux headless). On Windows, run the
    # full fail-closed validation below.
    if sys.platform != "win32":
        print("skipped: installer validation is a Windows build gate (non-Windows host)")
        return 0

    all_errors = (
        validate_required_files()
        + validate_required_dirs()
        + validate_installer_nsi()
        + validate_version_consistency()
    )

    if all_errors:
        for error in all_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Installer validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
