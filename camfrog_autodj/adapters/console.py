from __future__ import annotations
import sys
from .base import ChatAdapter, ChatMessage


class ConsoleAdapter(ChatAdapter):
    """stdin/stdout chat for testing. `!play x` = admin; `nick: !play x` = that user."""

    def __init__(self, cfg):
        self.prefix = cfg.prefix

    def messages(self):
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            if line.startswith(self.prefix):
                yield ChatMessage("console", line, local=True)
            elif ": " in line:
                u, t = line.split(": ", 1)
                yield ChatMessage(u, t)

    def send(self, text):
        print(f"[room] {text}", flush=True)
