#!/usr/bin/env python3
"""Check Windows 11 version and prerequisites.

This script replaces the inline PowerShell commands in the Makefile
to avoid shell quoting issues across different shells (bash, cmd, pwsh).
"""

import importlib.util
import os
import subprocess
import sys

WIN11_MIN_BUILD = 22000


def check_windows_version() -> tuple[bool, str]:
    """Check if Windows version is 11 (build 22000+)."""
    try:
        # Use PowerShell to get OS build number (works in both native and WSL)
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "(Get-Item 'C:\\Windows\\System32\\ntoskrnl.exe').VersionInfo.ProductVersion",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return False, "PowerShell command failed"

        # Parse output: e.g., "10.0.26300.1234"
        version_str = result.stdout.strip()
        parts = version_str.split(".")
        if len(parts) >= 3 and parts[2].isdigit():
            build = int(parts[2])
            return build >= WIN11_MIN_BUILD, f"Windows build {build}"

        return False, f"Could not parse build number from: {version_str}"
    except Exception as e:
        return False, f"Error checking Windows version: {e}"


def check_nsis() -> tuple[bool, str]:
    """Check if NSIS (makensis) is available."""
    # Check PATH first using appropriate command for platform
    if sys.platform == "win32":
        # Native Windows Python - use where
        for cmd in ["makensis", "makensis.exe"]:
            result = subprocess.run(["where", cmd], capture_output=True, text=True)
            if result.returncode == 0:
                return True, f"NSIS found in PATH: {result.stdout.strip()}"
    else:
        # WSL/Linux - use which
        for cmd in ["makensis", "makensis.exe"]:
            result = subprocess.run(["which", cmd], capture_output=True, text=True)
            if result.returncode == 0:
                return True, f"NSIS found in PATH: {result.stdout.strip()}"

    # Check common install locations (Windows paths work in WSL via /mnt/c/)
    common_paths = [
        r"C:\Program Files (x86)\NSIS\makensis.exe",
        r"C:\Program Files\NSIS\makensis.exe",
        "/mnt/c/Program Files (x86)/NSIS/makensis.exe",
        "/mnt/c/Program Files/NSIS/makensis.exe",
    ]
    for path in common_paths:
        if os.path.exists(path):
            return True, f"NSIS found at {path}"

    return False, "NSIS (makensis) not found. Install NSIS 3.09+ (choco install nsis)"


def check_mpv() -> tuple[bool, str]:
    """Check if mpv is available."""
    # Check PATH first using appropriate command for platform
    if sys.platform == "win32":
        # Native Windows Python - use where
        for cmd in ["mpv", "mpv.exe"]:
            result = subprocess.run(["where", cmd], capture_output=True, text=True)
            if result.returncode == 0:
                return True, f"mpv found in PATH: {result.stdout.strip()}"
    else:
        # WSL/Linux - use which
        for cmd in ["mpv", "mpv.exe"]:
            result = subprocess.run(["which", cmd], capture_output=True, text=True)
            if result.returncode == 0:
                return True, f"mpv found in PATH: {result.stdout.strip()}"

    # Check common install locations (Windows paths work in WSL via /mnt/c/)
    common_paths = [
        r"C:\Program Files\mpv\mpv.exe",
        r"C:\Program Files (x86)\mpv\mpv.exe",
        "/mnt/c/Program Files/mpv/mpv.exe",
        "/mnt/c/Program Files (x86)/mpv/mpv.exe",
    ]
    for path in common_paths:
        if os.path.exists(path):
            return True, f"mpv found at {path}"

    return False, "mpv.exe not found in PATH. Install: choco install mpv --yes"


def check_pyinstaller() -> tuple[bool, str]:
    """Check if PyInstaller is available."""
    if importlib.util.find_spec("PyInstaller") is not None:
        return True, "PyInstaller installed"
    return False, "PyInstaller not installed. Run: pip install pyinstaller"


def main():
    """Run all checks and return appropriate exit code."""
    checks = [
        ("Windows 11", check_windows_version),
        ("NSIS", check_nsis),
        ("mpv", check_mpv),
        ("PyInstaller", check_pyinstaller),
    ]

    all_passed = True
    for name, check_func in checks:
        passed, msg = check_func()
        status = "OK" if passed else "ERROR"
        print(f"  {status}: {msg}")
        if not passed and name != "mpv":  # mpv is warning only
            all_passed = False

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
