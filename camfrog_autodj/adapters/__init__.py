from __future__ import annotations

import logging

from .base import ChatAdapter

log = logging.getLogger(__name__)


class Composite(ChatAdapter):
    def __init__(self, reader: ChatAdapter, sender: ChatAdapter):
        self.reader, self.sender = reader, sender

    def messages(self):
        return self.reader.messages()

    def send(self, text):
        self.sender.send(text)

    def close(self):
        self.reader.close()
        if self.sender is not self.reader:
            self.sender.close()


def _make(kind: str, cfg) -> ChatAdapter:
    if kind == "console":
        from .console import ConsoleAdapter

        return ConsoleAdapter(cfg)
    if kind == "logtail":
        from .logtail import LogTailAdapter

        return LogTailAdapter(cfg)
    if kind == "uia":
        from .uia import UiaAdapter

        return UiaAdapter(cfg)
    raise ValueError(f"unknown chat adapter: {kind}")


def build_adapter(cfg) -> ChatAdapter:
    reader = _make(cfg.chat_reader, cfg)
    sender = reader if cfg.chat_sender == cfg.chat_reader else _make(cfg.chat_sender, cfg)
    return Composite(reader, sender)


class NullAdapter(ChatAdapter):
    """Fallback adapter when Camfrog cannot be reached (pywinauto missing, no room
    window open, ...). The GUI still opens; chat simply does nothing until Camfrog
    is available and discovery is re-run."""

    def messages(self):  # no chat lines ever
        return iter(())

    def send(self, text: str) -> None:
        # Deliberately do nothing: Camfrog is not reachable. Log a clear warning
        # so operators know messages are being dropped, not silently swallowed.
        log.warning(
            "Cannot send chat: Camfrog is not reachable (using NullAdapter). Message dropped: %r",
            text[:80],
        )

    def close(self) -> None:
        pass
