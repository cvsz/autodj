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


class ChatAdapter(ABC):
    @abstractmethod
    def messages(self) -> Iterator[ChatMessage]: ...

    @abstractmethod
    def send(self, text: str) -> None: ...

    def close(self) -> None:
        pass


def parse_line(line: str, rx: re.Pattern[str], is_im: bool = False) -> ChatMessage | None:
    m = rx.match(line.strip())
    return ChatMessage(m["user"].strip(), m["text"].strip(), is_im=is_im) if m else None


def diff_lines(prev: list[str], cur: list[str]) -> list[str]:
    """New lines in `cur`; handles growth and a scrolled/trimmed buffer."""
    for k in range(min(len(prev), len(cur)), 0, -1):
        if prev[-k:] == cur[:k]:
            return cur[k:]
    return cur if prev else []
