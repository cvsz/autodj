"""Create client-friendly launchers in dist/ (relative-path batch files + .lnk shortcuts)."""

from __future__ import annotations

from pathlib import Path

DIST = Path("dist")


def make_batch(name: str, args: str) -> None:
    """Write a batch file that launches AutoDJ.exe with relative paths."""
    content = f"""@echo off
rem AutoDJ - {args.strip() or "gui"}
rem Double-click to run. Works from any location.
cd /d "%~dp0"
start "" "AutoDJ.exe" {args}
"""
    (DIST / name).write_text(content, encoding="utf-8")


def main() -> None:
    if not DIST.is_dir():
        print("ERROR: dist/ not found. Run 'make portable' or 'portable.bat' first.")
        raise SystemExit(1)
    if not (DIST / "AutoDJ.exe").is_file():
        print("ERROR: dist/AutoDJ.exe not found.")
        raise SystemExit(1)

    make_batch("start.bat", "--gui")
    make_batch("check.bat", "--check")

    print("Created dist/start.bat   (double-click to run AutoDJ GUI)")
    print("Created dist/check.bat   (double-click to verify setup)")


if __name__ == "__main__":
    main()
