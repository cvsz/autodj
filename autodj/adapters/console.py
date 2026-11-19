from __future__ import annotations

import logging
import sys

from .base import ChatAdapter, ChatMessage

log = logging.getLogger(__name__)


class ConsoleAdapter(ChatAdapter):
    """stdin/stdout chat for testing. `!play x` = admin; `nick: !play x` = that user."""

    def __init__(self, cfg):
        self.prefix = cfg.prefix

    def test_connection(self) -> None:
        """Console adapter always works."""
        log.debug("Console adapter test_connection: OK")

    def messages(self):
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            if line.startswith(self.prefix):
                yield ChatMessage("console", line, local=True)
            elif line.startswith("im "):
                # `im nick: text` — an instant/private message; no room prefix required
                rest = line[3:].strip()
                if ": " in rest:
                    u, t = rest.split(": ", 1)
                    yield ChatMessage(u, t, is_im=True)
            elif ": " in line:
                u, t = line.split(": ", 1)
                yield ChatMessage(u, t)

    def send(self, text):
        print(f"[room] {text}", flush=True)
