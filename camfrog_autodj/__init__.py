"""CamfrogAutoDJ — Music bot for Camfrog rooms.

Enterprise-grade production release.  All public symbols are re-exported here
so operators can import from a single stable namespace.

Public API:
    Engine          — core playback + chat engine
    Config          — typed configuration with fail-closed validation
    ConfigError     — configuration validation failures
    AutoDJError     — base exception for all AutoDJ failures
    Track           — media track dataclass
    PlayQueue       — requests-first / autoplay-pool play queue
    PlaylistStore   — persistent playlist.json storage
    MpvPlayer       — one-mpv-per-track player with IPC control
    MessageRenderer — plain-text message renderer (GUI preview tags)
    build_adapter   — construct a ChatAdapter from config
    ChatMessage     — chat message dataclass
    ChatAdapter     — abstract chat adapter base
"""

from __future__ import annotations

from .adapters import (
    ChatAdapter,
    ChatMessage,
    NullAdapter,
    build_adapter,
)
from .config import Config, ConfigError, MessageStyle
from .engine import Engine
from .exceptions import (
    AutoDJError,
    BlockedUserError,
    ChatAdapterError,
    ChatError,
    ChatReadError,
    ChatSendError,
    ConfigValidationError,
    LibraryError,
    LibraryScanError,
    PlayerCrashError,
    PlayerError,
    PlayerHungError,
    PlayerNotAvailableError,
    QueueError,
    QueueFullError,
    RequestRateLimitError,
    SecurityError,
    TTSError,
    TTSUnavailableError,
    UnauthorizedError,
    UserError,
    YtdlpMissingError,
)
from .library import (
    MEDIA,
    SEARCH_PREFIX,
    LocalIndex,
    host_ok,
    is_url,
    local_track,
    parse_ytdlp_info,
    remote_tracks,
    scan_folder,
)
from .models import Track, fmt_time
from .playqueue import PlayQueue
from .renderer import MessageRenderer, RenderedMessage, get_renderer

__version__ = "0.3.0"

__all__ = [
    # Version
    "__version__",
    # Config
    "Config",
    "ConfigError",
    "MessageStyle",
    # Engine
    "Engine",
    # Exceptions
    "AutoDJError",
    "BlockedUserError",
    "ChatAdapterError",
    "ChatError",
    "ChatReadError",
    "ChatSendError",
    "ConfigValidationError",
    "LibraryError",
    "LibraryScanError",
    "PlayerCrashError",
    "PlayerError",
    "PlayerHungError",
    "PlayerNotAvailableError",
    "QueueError",
    "QueueFullError",
    "RequestRateLimitError",
    "SecurityError",
    "TTSError",
    "TTSUnavailableError",
    "UnauthorizedError",
    "YtdlpMissingError",
    # Library
    "MEDIA",
    "SEARCH_PREFIX",
    "LocalIndex",
    "host_ok",
    "is_url",
    "local_track",
    "parse_ytdlp_info",
    "remote_tracks",
    "scan_folder",
    # Models
    "Track",
    "UserError",
    "YtdlpMissingError",
    "fmt_time",
    # Play queue
    "PlayQueue",
    # Renderer
    "MessageRenderer",
    "RenderedMessage",
    "get_renderer",
    # Adapters
    "ChatAdapter",
    "ChatMessage",
    "NullAdapter",
    "build_adapter",
]
