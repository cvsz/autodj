"""Zip the source tree for distribution. Used by `make package` (a multi-line heredoc inside a Makefile
recipe does not work reliably across `make` implementations/shells, so this lives in its own script instead).
"""

from __future__ import annotations

import os
import sys
import zipfile

SKIP_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".git",
    ".venv",
    "dist",
    "build",
    "htmlcov",
    # runtime data, vendored binaries, evidence and forensic samples are not source
    "logs",
    "mpv",
    "evidence",
    "artifacts",
    "cert",
    "rea",
}
# Secrets and per-installation user data must never ship (dot-files are skipped too).
SKIP_FILES = {
    "config.toml",
    "config.toml.bak",
    "config.toml.tmp",
    "playlist.json",
    "playlist.json.bak",
    "playlist.json.tmp",
    "top_requests.json",
    "favorites.json",
    "plugin_stats.json",
    "AutoDJ.spec",
}
SKIP_SUFFIXES = (
    ".pyc",
    ".pfx",
    ".cer",
    ".pem",
    ".key",
    ".log",
    ".exe",
    ".dll",
    ".zip",
    ".pcap",
    ".dmp",
    ".spec",
)


def build(out_path: str, root: str = ".") -> str:
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for r, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            dirs[:] = [d for d in dirs if not d.startswith("runtime")]
            for f in sorted(files):
                if f.startswith(".") or f in SKIP_FILES or f.endswith(SKIP_SUFFIXES):
                    continue  # .env, .git-credentials, ... and user data
                path = os.path.join(r, f)
                z.write(path, os.path.relpath(path, root))
    return out_path


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: package.py OUT.zip", file=sys.stderr)
        sys.exit(2)
    out = build(sys.argv[1])
    print(out, os.path.getsize(out) // 1024, "KB")
