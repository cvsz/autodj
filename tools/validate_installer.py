#!/usr/bin/env python3
"""Validate NSIS installer structure and staged build payload."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "app.ico",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    "run_autodj.py",
    "config.example.toml",
    "install.ps1",
    "install.bat",
    "pyproject.toml",
]

REQUIRED_DIRS = [
    "mpv/_internal",
    "docs",
    "tools",
    "playlist",
]

REQUIRED_SECTIONS = [
    "SEC_MAIN",
    "SEC_MPV",
    "SEC_PLAYLIST",
    "SEC_DOCS",
    "SEC_TOOLS",
    "SEC_SCRIPTS",
]

REQUIRED_COMMANDS = [
    'File "dist\\AutoDJ.exe"',
    'File "dist\\app.ico"',
    'File /nonfatal "dist\\ads-list.json"',
    'File "dist\\config.toml"',
    'File /r "dist\\playlist\\*.json"',
    "ExecWait",
    "mpv-register.bat",
    "WriteUninstaller",
    "CreateShortcut",
    "WriteRegStr",
    "DeleteRegKey",
    "Section Uninstall",
]

REQUIRED_STAGED_FILES = [
    "AutoDJ.exe",
    "app.ico",
    "config.toml",
    "mpv/mpv.com",
    "mpv/yt-dlp.exe",
]

SECTION_PATTERN = re.compile(
    r'^\s*Section\s+(?:/o\s+)?(?:"[^"]+"\s+)?(\w+)',
    re.MULTILINE,
)


def validate_required_files() -> list[str]:
    return [
        f"missing required source file: {rel}"
        for rel in REQUIRED_FILES
        if not (ROOT / rel).is_file()
    ]


def validate_required_dirs() -> list[str]:
    return [
        f"missing required source directory: {rel}"
        for rel in REQUIRED_DIRS
        if not (ROOT / rel).is_dir()
    ]


def validate_staged_payload() -> list[str]:
    dist = ROOT / "dist"

    # Source validation must work without a completed build.
    if not (dist / "AutoDJ.exe").is_file():
        return []

    errors = [
        f"missing staged installer file: dist/{rel}"
        for rel in REQUIRED_STAGED_FILES
        if not (dist / rel).is_file()
    ]

    playlist_dir = dist / "playlist"
    if not playlist_dir.is_dir() or not any(playlist_dir.glob("*.json")):
        errors.append("missing staged playlist JSON files: dist/playlist/*.json")

    return errors


def _validate_installer_sections(content: str) -> list[str]:
    sections = SECTION_PATTERN.findall(content)
    return [
        f"missing required section: {section}"
        for section in REQUIRED_SECTIONS
        if section not in sections
    ]


def _validate_installer_commands(content: str) -> list[str]:
    return [
        f"missing required command in installer.nsi: {command}"
        for command in REQUIRED_COMMANDS
        if command not in content
    ]


def _validate_installer_common(content: str) -> list[str]:
    errors: list[str] = []

    if "RequestExecutionLevel user" not in content:
        errors.append("missing RequestExecutionLevel user")
    if 'InstallDir "$APPDATA' not in content:
        errors.append("missing APPDATA install directory")
    if "mpv-register.bat" not in content:
        errors.append("mpv-register.bat not referenced by installer")

    return errors


def _validate_uninstaller(content: str) -> list[str]:
    parts = content.split("Section Uninstall", 1)
    if len(parts) < 2:
        return ["missing uninstaller section"]

    body = parts[1].split("SectionEnd", 1)[0]
    errors: list[str] = []

    if 'Delete "$INSTDIR\\config.toml"' in body:
        errors.append("uninstaller deletes config.toml")
    if 'Delete "$INSTDIR\\playlist.json"' in body:
        errors.append("uninstaller deletes playlist.json")
    if "Keep config.toml, playlist.json, logs, playlists" not in body:
        errors.append("uninstaller missing user-data preservation comment")

    return errors


def _validate_vbcable_references(content: str) -> list[str]:
    errors: list[str] = []

    if "VBCABLE_Driver_Pack45" in content:
        errors.append("obsolete VB-CABLE Driver Pack 45 reference")

    if 'File "dist\\\\mpv\\\\vbcable\\\\' in content:
        errors.append("installer references an unstaged bundled VB-CABLE payload")

    return errors


def validate_installer_nsi() -> list[str]:
    """Validate installer.nsi structure and content."""
    path = ROOT / "installer.nsi"
    if not path.is_file():
        return ["installer.nsi not found"]

    content = path.read_text(encoding="utf-8")

    return (
        _validate_installer_sections(content)
        + _validate_installer_commands(content)
        + _validate_installer_common(content)
        + _validate_uninstaller(content)
        + _validate_vbcable_references(content)
    )


def validate_version_consistency() -> list[str]:
    try:
        import tomllib

        data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        project_version = data.get("project", {}).get("version", "unknown")
    except (OSError, ValueError, ImportError) as exc:
        return [f"could not read pyproject.toml version: {exc}"]

    content = (ROOT / "installer.nsi").read_text(encoding="utf-8")
    match = re.search(
        r'!define\s+/IfNDef\s+APP_VERSION\s+"([^"]+)"',
        content,
    )

    if match and match.group(1) != project_version:
        return [
            f"version mismatch: pyproject.toml={project_version}, installer.nsi={match.group(1)}"
        ]

    return []


def main() -> int:
    errors = (
        validate_required_files()
        + validate_required_dirs()
        + validate_staged_payload()
        + validate_installer_nsi()
        + validate_version_consistency()
    )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Installer validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
