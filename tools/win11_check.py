#!/usr/bin/env python3
"""Windows 11 prerequisite checks for Makefile."""

import os
import subprocess
import sys


def run_ps(cmd):
    """Run a PowerShell command and return (success, output)."""
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", cmd],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)


def check_windows11(min_build=22000):
    """Check if Windows 11 (build >= min_build)."""
    success, out, _err = run_ps(
        "$v = (Get-Item 'C:\\Windows\\System32\\ntoskrnl.exe').VersionInfo.ProductVersion; "
        "$build = [int]($v.Split('.')[2]); "
        "Write-Host $build; "
        "if ($build -lt " + str(min_build) + ") { exit 1 }"
    )
    if success:
        print(f"  OK: Windows 11 detected (build {out})")
        return True
    else:
        print(
            f"ERROR: Not Windows 11 (build < {min_build}). Install Windows 11 or set SKIP_CHECKS=1 to bypass."
        )
        return False


def check_nsis():
    """Check if NSIS (makensis) is available."""
    success, out, _err = run_ps(
        "if (Get-Command makensis -ErrorAction SilentlyContinue) { "
        "  echo '  OK: NSIS (makensis) in PATH' "
        "} elseif (Test-Path 'C:\\Program Files (x86)\\NSIS\\makensis.exe') { "
        "  echo '  OK: NSIS found at C:\\Program Files (x86)\\NSIS\\makensis.exe' "
        "} elseif (Test-Path 'C:\\Program Files\\NSIS\\makensis.exe') { "
        "  echo '  OK: NSIS found at C:\\Program Files\\NSIS\\makensis.exe' "
        "} else { "
        "  echo 'ERROR: NSIS (makensis) not found. Install NSIS 3.09+ (choco install nsis) or set SKIP_CHECKS=1 to bypass.'; "
        "  exit 1 "
        "}"
    )
    if success:
        print(f"  {out}")
        return True
    else:
        print(f"ERROR: {out}")
        return False


def check_mpv():
    """Check if mpv is available."""
    success, out, _err = run_ps(
        "if (Get-Command mpv.exe -ErrorAction SilentlyContinue) { "
        "  echo '  OK: mpv.exe in PATH' "
        "} elseif (Test-Path 'C:\\Program Files\\mpv\\mpv.exe') { "
        "  echo '  OK: mpv found at C:\\Program Files\\mpv\\mpv.exe' "
        "} else { "
        "  echo 'WARN: mpv.exe not found in PATH. Install: choco install mpv --yes' "
        "}"
    )
    print(f"  {out}")
    return True  # mpv is a warning, not an error


def check_pyinstaller(pip_cmd):
    """Check if PyInstaller is installed."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import PyInstaller"], capture_output=True, check=False
        )
        if result.returncode == 0:
            print("  OK: PyInstaller installed")
            return True
        else:
            print(f"WARN: PyInstaller not installed. Run: {pip_cmd} install pyinstaller")
            return True  # PyInstaller is a warning, not an error
    except Exception:
        print(f"WARN: PyInstaller not installed. Run: {pip_cmd} install pyinstaller")
        return True


def _run_win11_check(skip_checks, min_build, pip_cmd, log_dir, log_ts):
    """Run the full win11-check."""
    log_file = os.path.join(log_dir, f"win11-check-{log_ts}.log")

    def log(msg):
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")

    print(f"=== Windows 11 Prerequisite Check ({log_ts}) ===")
    log(f"=== Windows 11 Prerequisite Check ({log_ts}) ===")

    if skip_checks:
        msg = "  SKIP: prerequisite checks disabled (SKIP_CHECKS=1)"
        print(msg)
        log(msg)
    else:
        if not check_windows11(min_build):
            return False
        log("  OK: Windows 11 detected")

        if not check_nsis():
            return False

        check_mpv()
        check_pyinstaller(pip_cmd)

    print(f"Logs: {log_file}")
    return True


def _run_simple_check(cmd_name, check_func, skip_checks, log_dir, log_ts):
    """Run a simple check (mpv-check, nsis-check, pyinstaller-check)."""
    log_file = os.path.join(log_dir, f"{cmd_name}-{log_ts}.log")

    if skip_checks:
        msg = f"  SKIP: {cmd_name} check disabled (SKIP_CHECKS=1)"
        print(msg)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    else:
        check_func()


def main():
    if len(sys.argv) < 2:
        print("Usage: python win11_check.py <command> [args...]")
        sys.exit(1)

    cmd = sys.argv[1]
    skip_checks = os.environ.get("SKIP_CHECKS") == "1"
    min_build = int(os.environ.get("WIN11_MIN_BUILD", "22000"))
    pip_cmd = os.environ.get("PIP", f"{sys.executable} -m pip")
    log_dir = os.environ.get("BUILD_LOG_DIR", "logs")
    log_ts = os.environ.get("BUILD_LOG_TS", "unknown")

    os.makedirs(log_dir, exist_ok=True)

    if cmd == "win11-check":
        ok = _run_win11_check(skip_checks, min_build, pip_cmd, log_dir, log_ts)
        sys.exit(0 if ok else 1)

    elif cmd == "mpv-check":
        _run_simple_check("mpv-check", check_mpv, skip_checks, log_dir, log_ts)

    elif cmd == "nsis-check":
        _run_simple_check("nsis-check", check_nsis, skip_checks, log_dir, log_ts)

    elif cmd == "pyinstaller-check":
        _run_simple_check(
            "pyinstaller-check", lambda: check_pyinstaller(pip_cmd), skip_checks, log_dir, log_ts
        )

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
