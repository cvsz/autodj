"""Enterprise-grade exception hierarchy for CamfrogAutoDJ.

All exceptions inherit from ``AutoDJError`` so operators can catch the
base class for any AutoDJ-specific failure.  Each exception carries a
structured ``code`` (machine-readable) and ``details`` (operator-facing)
so the GUI, logs, and CLI can all render consistent messages.

Never raise these with user-controlled data in the message — that would
be an injection vector.  Always pass sanitized values.
"""

from __future__ import annotations

from typing import Any


class AutoDJError(Exception):
    """Base exception for all AutoDJ failures.

    Attributes:
        code: Machine-readable error code (e.g. ``config.invalid``,
            ``chat.send_failed``, ``player.hung``).
        details: Human-readable details safe to show in the GUI or log.
        context: Additional structured context for debugging.
    """

    code: str
    details: str
    context: dict[str, Any]

    def __init__(
        self,
        message: str,
        *,
        code: str = "autodj.error",
        details: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.details = details or message
        self.context = context or {}

    def __str__(self) -> str:
        return f"[{self.code}] {super().__str__()}"


# ---- Configuration errors --------------------------------------------------


class ConfigError(AutoDJError):
    """Configuration is invalid, unreadable, or missing required values."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "config.error",
        details: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message, code=code, details=details, context=context)


class ConfigValidationError(ConfigError):
    """A config value failed validation (type, range, regex, or semantic)."""

    def __init__(
        self, message: str, *, field: str | None = None, context: dict[str, Any] | None = None
    ):
        merged_context: dict[str, Any] = context.copy() if context else {}
        if field:
            merged_context["field"] = field
        super().__init__(
            message,
            code="config.validation",
            details=message,
            context=merged_context,
        )


# ---- Chat / UIA errors -----------------------------------------------------


class ChatError(AutoDJError):
    """Base class for chat read/send failures."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "chat.error",
        details: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message, code=code, details=details, context=context)


class ChatSendError(ChatError):
    """A message could not be delivered to the Camfrog room."""

    def __init__(
        self, message: str, *, details: str | None = None, context: dict[str, Any] | None = None
    ):
        super().__init__(message, code="chat.send_failed", details=details, context=context)


class ChatReadError(ChatError):
    """The chat reader (UIA / logtail / console) failed to read messages."""

    def __init__(
        self, message: str, *, details: str | None = None, context: dict[str, Any] | None = None
    ):
        super().__init__(message, code="chat.read_failed", details=details, context=context)


class ChatAdapterError(ChatError):
    """The chat adapter is misconfigured or unavailable."""

    def __init__(
        self, message: str, *, details: str | None = None, context: dict[str, Any] | None = None
    ):
        super().__init__(message, code="chat.adapter_error", details=details, context=context)


# ---- Player / mpv errors ---------------------------------------------------


class PlayerError(AutoDJError):
    """Base class for mpv playback failures."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "player.error",
        details: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message, code=code, details=details, context=context)


class PlayerNotAvailableError(PlayerError):
    """mpv is not installed or not on PATH."""

    def __init__(
        self, message: str, *, details: str | None = None, context: dict[str, Any] | None = None
    ):
        super().__init__(message, code="player.not_available", details=details, context=context)


class PlayerHungError(PlayerError):
    """mpv did not exit within the grace period."""

    def __init__(
        self, message: str, *, details: str | None = None, context: dict[str, Any] | None = None
    ):
        super().__init__(message, code="player.hung", details=details, context=context)


class PlayerCrashError(PlayerError):
    """mpv exited with a non-zero code."""

    def __init__(
        self, message: str, *, details: str | None = None, context: dict[str, Any] | None = None
    ):
        super().__init__(message, code="player.crashed", details=details, context=context)


# ---- Library / yt-dlp errors ----------------------------------------------


class LibraryError(AutoDJError):
    """Base class for media library / yt-dlp failures."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "library.error",
        details: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message, code=code, details=details, context=context)


class YtdlpMissingError(LibraryError):
    """yt-dlp executable or Python module is not available."""

    def __init__(
        self, message: str, *, details: str | None = None, context: dict[str, Any] | None = None
    ):
        super().__init__(message, code="library.yt_dlp_missing", details=details, context=context)


class LibraryScanError(LibraryError):
    """A music folder could not be scanned."""

    def __init__(
        self, message: str, *, details: str | None = None, context: dict[str, Any] | None = None
    ):
        super().__init__(message, code="library.scan_failed", details=details, context=context)


# ---- Queue / request errors ------------------------------------------------


class QueueError(AutoDJError):
    """Base class for play queue failures."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "queue.error",
        details: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message, code=code, details=details, context=context)


class QueueFullError(QueueError):
    """The request queue has reached its configured maximum length."""

    def __init__(
        self, message: str, *, details: str | None = None, context: dict[str, Any] | None = None
    ):
        super().__init__(message, code="queue.full", details=details, context=context)


class RequestRateLimitError(QueueError):
    """A user exceeded their per-window request limit."""

    def __init__(
        self, message: str, *, details: str | None = None, context: dict[str, Any] | None = None
    ):
        super().__init__(message, code="queue.rate_limited", details=details, context=context)


# ---- TTS errors ------------------------------------------------------------


class TTSError(AutoDJError):
    """Base class for text-to-speech failures."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "tts.error",
        details: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message, code=code, details=details, context=context)


class TTSUnavailableError(TTSError):
    """pyttsx3 is not installed or the SAPI backend is unavailable."""

    def __init__(
        self, message: str, *, details: str | None = None, context: dict[str, Any] | None = None
    ):
        super().__init__(message, code="tts.unavailable", details=details, context=context)


# ---- Security / authorization errors --------------------------------------


class SecurityError(AutoDJError):
    """Base class for authorization / security violations."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "security.error",
        details: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message, code=code, details=details, context=context)


class UnauthorizedError(SecurityError):
    """A user attempted an action they are not authorized for."""

    def __init__(
        self, message: str, *, details: str | None = None, context: dict[str, Any] | None = None
    ):
        super().__init__(message, code="security.unauthorized", details=details, context=context)


class BlockedUserError(SecurityError):
    """A blocked user attempted to issue a command."""

    def __init__(
        self, message: str, *, details: str | None = None, context: dict[str, Any] | None = None
    ):
        super().__init__(message, code="security.blocked_user", details=details, context=context)


# ---- Aliases for backward compatibility ------------------------------------


# UserError is the original AutoDJ exception (messages safe to show in the room).
# Kept as an alias in exceptions.py so existing ``except UserError`` clauses keep working.
UserError = AutoDJError


__all__ = [
    "AutoDJError",
    "ConfigError",
    "ConfigValidationError",
    "ChatError",
    "ChatSendError",
    "ChatReadError",
    "ChatAdapterError",
    "PlayerError",
    "PlayerNotAvailableError",
    "PlayerHungError",
    "PlayerCrashError",
    "LibraryError",
    "YtdlpMissingError",
    "LibraryScanError",
    "QueueError",
    "QueueFullError",
    "RequestRateLimitError",
    "TTSError",
    "TTSUnavailableError",
    "SecurityError",
    "UnauthorizedError",
    "BlockedUserError",
    "UserError",
]
