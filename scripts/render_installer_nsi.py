#!/usr/bin/env python3
"""Render ``installer.nsi`` with a concrete ``APP_VERSION``.

Both the PowerShell and the Linux/Wine installer builders use this helper so
the version-substitution rule lives in exactly one place.  It replaces the
default value of either form:

    !define /IfNDef APP_VERSION "0.3.0"
    !define APP_VERSION "0.3.0"

The build scripts additionally pass ``/DAPP_VERSION=<version>`` to makensis;
NSIS lets a command-line define override ``!define /IfNDef``, so a stale
default can never decide the artifact name again.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

VERSION_PATTERN = re.compile(
    r'(?m)^(?P<prefix>!define[ \t]+(?:/IfNDef[ \t]+)?APP_VERSION[ \t]+")'
    r'(?P<version>[^"]*)'
    r'(?P<suffix>")'
)
# Versions come from pyproject.toml or a release tag.  Keep them to characters
# that are safe in a quoted NSIS define and in an output filename.
SAFE_VERSION = re.compile(r"^[0-9A-Za-z][0-9A-Za-z.+_-]*$")


def render(template: str, version: str) -> str:
    """Return ``template`` with its APP_VERSION default replaced by ``version``."""
    if not SAFE_VERSION.match(version):
        raise ValueError(f"unsafe version string: {version!r}")

    rendered, count = VERSION_PATTERN.subn(
        lambda match: f"{match.group('prefix')}{version}{match.group('suffix')}",
        template,
    )
    if count != 1:
        raise ValueError(
            f"expected exactly one APP_VERSION define in installer.nsi, found {count}"
        )
    return rendered


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="version to render")
    parser.add_argument("--input", default="installer.nsi", help="template path")
    parser.add_argument("--output", required=True, help="rendered script path")
    args = parser.parse_args(argv)

    try:
        template = Path(args.input).read_text(encoding="utf-8")
        rendered = render(template, args.version)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(f"Rendered {args.input} -> {args.output} (APP_VERSION={args.version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
