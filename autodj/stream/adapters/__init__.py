"""Multi-platform stream adapters for AutoDJ.

Adapters connect AutoDJ to social platforms via probe accounts so users on
YouTube, TikTok, Facebook, and Camfrog can request songs and control the bot.
Each adapter implements:

- :meth:`connect` - authenticate with a probe account and open the channel
- :meth:`messages` - yield incoming chat/comment messages as ChatMessage
- :meth:`send` - post a message back to the platform
- :meth:`close` - cleanly disconnect

Ported design patterns from cvsz/streamdbc (Go) adapted to Python.
"""

from __future__ import annotations

from .base import AdapterError, AdapterState, ChatMessage, StreamAdapter

__all__ = [
    "StreamAdapter",
    "ChatMessage",
    "AdapterState",
    "AdapterError",
]
