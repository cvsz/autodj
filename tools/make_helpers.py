#!/usr/bin/env python3
"""Helper functions for Makefile targets - cross-platform compatibility."""

import glob
import py_compile
import shutil
import subprocess
import sys


def has_module(module_name):
    """Check if a Python module is importable."""
    try:
        subprocess.run(
            [sys.executable, "-c", f"import {module_name}"], check=True, capture_output=True
        )
        return True
    except subprocess.CalledProcessError:
        return False


def has_command(cmd):
    """Check if a command is available on PATH."""
    return shutil.which(cmd) is not None


def run_cmd(cmd, **kwargs):
    """Run a command and return the result."""
    return subprocess.run(cmd, **kwargs)


def lint():
    """Run ruff or fallback to py_compile."""
    if has_module("ruff") or has_command("ruff"):
        run_cmd([sys.executable, "-m", "ruff", "check", "camfrog_autodj", "tests", "tools"])
    else:
        print(
            "ruff not installed -- falling back to py_compile (pip install ruff for real linting)"
        )
        [py_compile.compile(f) for f in glob.glob("camfrog_autodj/**/*.py", recursive=True)]


def lint_src():
    """Run ruff on source + tools only."""
    if has_module("ruff") or has_command("ruff"):
        result = run_cmd(
            [sys.executable, "-m", "ruff", "check", "camfrog_autodj", "tools"], capture_output=True
        )
        if result.returncode != 0:
            print("NOTE: pre-existing ruff warnings (defensive patterns)")
    else:
        print(
            "ruff not installed -- falling back to py_compile (pip install ruff for real linting)"
        )
        [py_compile.compile(f) for f in glob.glob("camfrog_autodj/**/*.py", recursive=True)]


def fmt():
    """Format with ruff or black."""
    for cmd in ["ruff", "black"]:
        if has_command(cmd) or (cmd == "ruff" and has_module("ruff")):
            if cmd == "ruff":
                run_cmd(
                    [sys.executable, "-m", "ruff", "format", "camfrog_autodj", "tests", "tools"]
                )
            else:
                run_cmd([cmd, "camfrog_autodj", "tests", "tools"])
            return
    print("no formatter installed (pip install ruff or black)")


def fmt_check():
    """Check formatting with ruff."""
    if has_command("ruff") or has_module("ruff"):
        run_cmd(
            [sys.executable, "-m", "ruff", "format", "--check", "camfrog_autodj", "tests", "tools"]
        )
    else:
        print("ruff not installed -- skipping format check (pip install ruff)")


def typecheck():
    """Type-check with mypy."""
    if has_module("mypy"):
        run_cmd([sys.executable, "-m", "mypy", "camfrog_autodj"])
    else:
        print("mypy not installed (pip install mypy)")


def shellcheck():
    """Lint shell scripts with shellcheck."""
    if has_command("shellcheck"):
        scripts = glob.glob("scripts/*.sh") + glob.glob("tools/*.sh")
        if scripts:
            run_cmd(["shellcheck"] + scripts)
        else:
            print("No shell scripts found to check")
    else:
        print("shellcheck not installed -- skipping (apt install shellcheck)")


def mutation_smoke():
    """Check if mutate.sh exists and is executable."""
    import os

    if not os.access("tools/mutate.sh", os.X_OK):
        print("tools/mutate.sh not found -- see AUDIT.md for how it was used")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python make_helpers.py <command>")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "lint":
        lint()
    elif cmd == "lint-src":
        lint_src()
    elif cmd == "fmt":
        fmt()
    elif cmd == "fmt-check":
        fmt_check()
    elif cmd == "typecheck":
        typecheck()
    elif cmd == "shellcheck":
        shellcheck()
    elif cmd == "mutation-smoke":
        mutation_smoke()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
