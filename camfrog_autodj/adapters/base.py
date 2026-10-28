from __future__ import annotations
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator


@dataclass
class ChatMessage:
    user: str
    text: str
    local: bool = False  # from the local console: always trusted as admin


class ChatAdapter(ABC):
    @abstractmethod
    def messages(self) -> Iterator[ChatMessage]: ...

    @abstractmethod
    def send(self, text: str) -> None: ...

    def close(self) -> None:
        pass


def parse_line(line: str, rx: "re.Pattern[str]") -> ChatMessage | None:
    m = rx.match(line.strip())
    return ChatMessage(m["user"].strip(), m["text"].strip()) if m else None


def diff_lines(prev: list[str], cur: list[str]) -> list[str]:
    """New lines in `cur`; handles growth and a scrolled/trimmed buffer."""
    for k in range(min(len(prev), len(cur)), 0, -1):
        if prev[-k:] == cur[:k]:
            return cur[k:]
    return cur if prev else []
