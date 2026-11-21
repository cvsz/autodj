"""Guard: no local config copies or API keys in tracked files.

a90226f committed config.toml.bak-imjoin (a local backup holding a live
ai_api_key) to this public repository.  These tests fail the build before
that can happen again.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Real config files are allowed only as fixtures under tests/ or tools/.
_CONFIG_COPY = re.compile(r"(^|/)config\.toml(\.[^/]+)?$")
_ALLOWED_CONFIG_DIRS = ("tests/", "tools/")

# Provider key formats.  Matching is on tracked text files; the value is never printed.
_SECRET = re.compile(
    r"(ghp_[A-Za-z0-9]{30,}"
    r"|github_pat_[A-Za-z0-9_]{30,}"
    r"|sk-(?:proj-)?[A-Za-z0-9_-]{32,}"
    r"|nvapi-[A-Za-z0-9_-]{30,}"
    r"|AKIA[0-9A-Z]{16}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}"
    r"|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)


def _tracked() -> list[str]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    return [p for p in out.decode("utf-8", "replace").split("\0") if p]


def test_no_local_config_copies_are_tracked():
    bad = [
        p for p in _tracked() if _CONFIG_COPY.search(p) and not p.startswith(_ALLOWED_CONFIG_DIRS)
    ]
    assert bad == [], f"local config files are tracked (may hold ai_api_key): {bad}"


def test_config_backups_are_gitignored():
    names = ["config.toml", "config.toml.bak", "config.toml.bak-ai", "config.toml.bak-20261121"]
    try:
        res = subprocess.run(
            ["git", "check-ignore", "--no-index", *names],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
    except OSError:
        pytest.skip("git not available")
    ignored = set(res.stdout.split())
    assert ignored == set(names), f"not ignored: {sorted(set(names) - ignored)}"
    example = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", "config.example.toml"], cwd=ROOT
    )
    assert example.returncode == 1, "config.example.toml must stay tracked"


def test_no_api_keys_in_tracked_files():
    leaks: list[str] = []
    for rel in _tracked():
        path = ROOT / rel
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if b"\0" in data[:4096]:  # binary
            continue
        for n, line in enumerate(data.decode("utf-8", "replace").splitlines(), 1):
            if _SECRET.search(line):
                leaks.append(f"{rel}:{n}")
    assert leaks == [], f"possible credentials committed at: {leaks}"
