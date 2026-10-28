"""Small pure text helpers shared by the engine and the Windows chat sender."""
from __future__ import annotations
import re

_CTRL = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def clean_text(s: str) -> str:
    """One line, no control characters (they would be typed into the room as keystrokes), single spaces."""
    return " ".join(_CTRL.sub(" ", s).split())


def norm(s: str) -> str:
    """Comparison form of a chat line: NBSP/whitespace collapsed, case kept."""
    return " ".join(s.replace("\xa0", " ").split())
