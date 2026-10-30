from __future__ import annotations

from .base import ChatAdapter


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
    sender = (
        reader if cfg.chat_sender == cfg.chat_reader else _make(cfg.chat_sender, cfg)
    )
    return Composite(reader, sender)
