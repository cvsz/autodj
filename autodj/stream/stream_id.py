"""Safe stream/room identifier validation.

Ported from cvsz/streamdbc internal/core/stream_id.go.

Stream/room IDs must be URL-safe and filesystem-safe: they may appear in
HLS segment paths, recording filenames, Redis keys, and API URLs, so we
restrict them to alphanumeric characters plus ``-`` ``_`` ``.`` and require
the first character to be a letter or digit.
"""

from __future__ import annotations

from typing import Final

MAX_STREAM_ID_LENGTH: Final[int] = 128
MAX_STREAM_NAME_LENGTH: Final[int] = 256


class StreamIDError(ValueError):
    """Raised when a stream/room ID or name is invalid."""


def _is_start_char(ch: str) -> bool:
    return ch.isalnum()


def _is_body_char(ch: str) -> bool:
    return ch.isalnum() or ch in ("-", "_", ".")


def validate_stream_id(stream_id: str) -> None:
    """Validate *stream_id* as a safe identifier for URLs and filesystem paths.

    Raises :class:`StreamIDError` if the ID is empty, too long, starts with a
    non-alphanumeric character, or contains characters outside
    ``[A-Za-z0-9-_.]``.
    """
    if not stream_id or len(stream_id) > MAX_STREAM_ID_LENGTH:
        raise StreamIDError(f"stream id must contain 1-{MAX_STREAM_ID_LENGTH} characters")
    if not _is_start_char(stream_id[0]):
        raise StreamIDError("stream id must start with a letter or digit")
    for ch in stream_id:
        if not _is_body_char(ch):
            raise StreamIDError(
                f"stream id contains invalid character {ch!r}; allowed: letters, digits, -, _, ."
            )


def validate_stream_name(name: str) -> None:
    """Validate a human-readable stream/room *name*.

    Raises :class:`StreamIDError` if the name is empty, too long, or contains
    control characters.
    """
    name = (name or "").strip()
    if not name or len(name) > MAX_STREAM_NAME_LENGTH:
        raise StreamIDError(f"stream name must contain 1-{MAX_STREAM_NAME_LENGTH} characters")
    for ch in name:
        if ord(ch) < 32 or ord(ch) == 127:
            raise StreamIDError("stream name contains a control character")
