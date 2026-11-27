"""Create client-friendly launchers in dist/ (relative-path batch files + .lnk shortcuts).

Usage: python tools/make_client_shortcuts.py [DIST_DIR]   (default: dist)
"""

from __future__ import annotations

import sys
from pathlib import Path


def make_batch(dist: Path, name: str, args: str) -> None:
    """Write a batch file that launches zAutoDJ.exe with relative paths."""
    content = f"""@echo off
rem AutoDJ - {args.strip() or "gui"}
rem Double-click to run. Works from any location.
cd /d "%~dp0"
start "" "zAutoDJ.exe" {args}
"""
    (dist / name).write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    dist = Path(args[0]) if args else Path("dist")
    if not dist.is_dir():
        print(f"ERROR: {dist}/ not found. Run 'make portable' or 'portable.bat' first.")
        raise SystemExit(1)
    if not (dist / "zAutoDJ.exe").is_file():
        print(f"ERROR: {dist}/zAutoDJ.exe not found.")
        raise SystemExit(1)

    make_batch(dist, "start.bat", "--gui")
    make_batch(dist, "check.bat", "--check")

    print(f"Created {dist}/start.bat   (double-click to run AutoDJ GUI)")
    print(f"Created {dist}/check.bat   (double-click to verify setup)")


if __name__ == "__main__":
    main()
