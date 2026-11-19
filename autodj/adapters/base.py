from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass


@dataclass
class ChatMessage:
    user: str
    text: str
    local: bool = False  # from the local console: always trusted as admin
    is_im: bool = False  # instant/private message: can control the bot without room prefix
    event: str = ""  # "" for a chat line; "join" when the room reported this user entering


class ChatAdapter(ABC):
    @abstractmethod
    def messages(self) -> Iterator[ChatMessage]: ...

    @abstractmethod
    def send(self, text: str) -> None: ...

    def close(self) -> None:  # noqa: B027  # intentional no-op base; adapters that hold resources override close()
        pass


def parse_line(line: str, rx: re.Pattern[str], is_im: bool = False) -> ChatMessage | None:
    m = rx.match(line.strip())
    if not m:
        return None
    user, text = m["user"].strip(), m["text"].strip()
    # Camfrog prefixes private messages onto the nick; strip the marker so the
    # IM viewer and nickname auth see the real sender.  The marker must be a
    # separate word (followed by whitespace): Camfrog nicknames cannot contain
    # spaces, so a *nick* such as "[IM]Admin" is never rewritten to "Admin"
    # (that would hand the "Admin" nickname's privileges to another user).
    for marker in ("IM", "IM:", "[IM]", "(IM)", "PM", "Private:"):
        head, sep, rest = user.partition(" ")
        if head == marker and sep and rest.strip():
            user = rest.strip()
            is_im = True
            break
    return ChatMessage(user, text, is_im=is_im)


def parse_join(line: str, rx: re.Pattern[str] | None) -> ChatMessage | None:
    """A room notice that *user* entered (matched by ``join_line_regex``), else None."""
    if rx is None:
        return None
    m = rx.search(line.strip())
    if not m:
        return None
    # The pattern may offer alternatives (user, user_th, ...): take the group that matched.
    user = next((v for k, v in m.groupdict().items() if k.startswith("user") and v), "")
    return ChatMessage(user.strip(), "", event="join") if user.strip() else None


def compile_join_rx(pattern: str) -> re.Pattern[str] | None:
    """Compile ``join_line_regex``; empty disables join detection."""
    return re.compile(pattern) if pattern.strip() else None


def diff_lines(prev: list[str], cur: list[str]) -> list[str]:
    """New lines in `cur`; handles growth and a scrolled/trimmed buffer."""
    for k in range(min(len(prev), len(cur)), 0, -1):
        if prev[-k:] == cur[:k]:
            return cur[k:]
    return cur if prev else []
