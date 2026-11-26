"""Small pure text helpers shared by the engine and the Windows chat sender."""

from __future__ import annotations

import re
import sys

_CTRL = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def clean_text(s: str) -> str:
    """One line, no control characters (they would be typed into the room as keystrokes), single spaces."""
    return " ".join(_CTRL.sub(" ", s).split())


def norm(s: str) -> str:
    """Comparison form of a chat line: NBSP/whitespace collapsed, case kept."""
    return " ".join(s.replace("\xa0", " ").split())


def safe_print(*args, **kwargs) -> None:
    """Print that never raises ``UnicodeEncodeError`` on a restricted console codepage.

    Windows consoles use codepages such as cp874 (Thai), cp1252, etc.  Any text
    containing a character outside that codepage (e.g. an emoji or non-Thai
    Unicode in a Camfrog window title or chat line) makes ``print()`` raise and
    crash the whole process.  This wrapper tries normal ``print()`` first, and
    on ``UnicodeEncodeError`` re-encodes with ``errors="replace"`` so output
    always succeeds (unrepresentable characters become ``?`` or the codepage's
    substitute glyph).
    """
    file = kwargs.get("file", sys.stdout)
    if file is None:  # no console (pythonw / windowed exe): nothing to print to
        return
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    flush = kwargs.get("flush", False)
    encoding = getattr(file, "encoding", None) or "utf-8"
    text = sep.join(str(a) for a in args) + end
    try:
        file.write(text)
    except UnicodeEncodeError:
        file.write(text.encode(encoding, errors="replace").decode(encoding))
    if flush:
        file.flush()
