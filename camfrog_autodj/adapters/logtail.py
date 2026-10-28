from __future__ import annotations
import re
import time
from pathlib import Path
from .base import ChatAdapter, parse_line


class LogTailAdapter(ChatAdapter):
    """Reads a chat log file as it grows. Read-only: pair with chat_sender="uia"."""

    def __init__(self, cfg):
        self.path = Path(cfg.log_path)
        self.enc = cfg.log_encoding
        self.rx = re.compile(cfg.line_regex)

    def messages(self):
        with open(self.path, "r", encoding=self.enc, errors="replace") as f:
            f.seek(0, 2)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.3)
                    continue
                m = parse_line(line.rstrip("\r\n"), self.rx)
                if m:
                    yield m

    def send(self, text):
        raise NotImplementedError("logtail is read-only")
