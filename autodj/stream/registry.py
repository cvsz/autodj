"""Thread-safe stream/room registry.

Ported from cvsz/streamdbc internal/core/registry.go.

Tracks active streams across platforms (Camfrog, YouTube Live, TikTok Live,
Facebook Live, etc.) with lifecycle states:

- IDLE    - registered but not broadcasting
- LIVE    - actively broadcasting
- RECORDING - FFmpeg recording in progress
- ERROR   - stream encountered an error

All access is protected by a reentrant read/write lock.  StreamInfo snapshots
are cloned on read so callers cannot mutate internal state.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from .stream_id import (
    validate_stream_id,
    validate_stream_name,
)


class StreamError(Exception):
    """Stream registry error."""


class StreamState(str):
    IDLE = "IDLE"
    LIVE = "LIVE"
    RECORDING = "RECORDING"
    ERROR = "ERROR"


_VALID_STATES = frozenset(
    {StreamState.IDLE, StreamState.LIVE, StreamState.RECORDING, StreamState.ERROR}
)


@dataclass
class StreamInfo:
    """Immutable snapshot of a stream's current state."""

    id: str
    name: str
    state: str = StreamState.IDLE
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    codec: str = ""
    bitrate: int = 0
    viewers: int = 0
    publisher_ip: str = ""
    metadata: dict = field(default_factory=dict)
    last_activity_at: Optional[datetime] = None

    def clone(self) -> "StreamInfo":
        """Return a deep copy safe for external mutation."""
        return StreamInfo(
            id=self.id,
            name=self.name,
            state=self.state,
            created_at=self.created_at,
            started_at=self.started_at,
            codec=self.codec,
            bitrate=self.bitrate,
            viewers=self.viewers,
            publisher_ip=self.publisher_ip,
            metadata=dict(self.metadata),
            last_activity_at=self.last_activity_at,
        )


class StreamRegistry:
    """Thread-safe registry of active streams."""

    def __init__(self, stream_ttl_seconds: float = 24 * 3600.0) -> None:
        self._lock = threading.RLock()
        self._streams: dict[str, StreamInfo] = {}
        self._stream_ttl = stream_ttl_seconds

    def register(self, stream_id: str, name: Optional[str] = None) -> StreamInfo:
        """Register a new stream and return its info snapshot."""
        validate_stream_id(stream_id)
        if name is None or not name.strip():
            name = stream_id
        else:
            name = name.strip()
            validate_stream_name(name)

        with self._lock:
            if stream_id in self._streams:
                raise StreamError("stream already exists")
            now = datetime.now(timezone.utc)
            info = StreamInfo(
                id=stream_id,
                name=name,
                state=StreamState.IDLE,
                created_at=now,
                last_activity_at=now,
            )
            self._streams[stream_id] = info
            return info.clone()

    def get(self, stream_id: str) -> Optional[StreamInfo]:
        """Return a clone of the stream info, or None if not found."""
        with self._lock:
            info = self._streams.get(stream_id)
            if info is None:
                return None
            return info.clone()

    def update(  # noqa: C901 - complex state machine with validation
        self,
        stream_id: str,
        updater,
    ) -> None:
        """Apply *updater* to a clone of the stream, then persist if valid.

        The updater receives a mutable clone outside the lock.  After the
        updater returns, the clone is validated and written back under the
        write lock (last-writer-wins).
        """
        if updater is None:
            raise StreamError("stream updater is required")

        with self._lock:
            info = self._streams.get(stream_id)
            if info is None:
                raise StreamError("stream not found")
            candidate = info.clone()

        updater(candidate)

        if candidate.id != stream_id:
            raise StreamError("invalid stream id in updater")
        validate_stream_id(candidate.id)
        candidate.name = candidate.name.strip()
        validate_stream_name(candidate.name)
        if candidate.state not in _VALID_STATES:
            raise StreamError("invalid stream state")
        if candidate.viewers < 0:
            raise StreamError("viewer count cannot be negative")
        if candidate.bitrate < 0:
            raise StreamError("bitrate cannot be negative")
        for key, value in candidate.metadata.items():
            if not key.strip() or "\x00" in key or "\r" in key or "\n" in key:
                raise StreamError("metadata key is invalid")
            if "\x00" in value or "\r" in value or "\n" in value:
                raise StreamError("metadata value is invalid")

        now = datetime.now(timezone.utc)
        with self._lock:
            current = self._streams.get(stream_id)
            if current is None:
                raise StreamError("stream not found")
            current.state = candidate.state
            current.name = candidate.name
            current.codec = candidate.codec
            current.bitrate = candidate.bitrate
            current.viewers = candidate.viewers
            current.publisher_ip = candidate.publisher_ip
            current.metadata = dict(candidate.metadata)
            current.last_activity_at = now
            if candidate.state == StreamState.LIVE and current.started_at is None:
                current.started_at = now
            elif candidate.state != StreamState.LIVE:
                current.started_at = None

    def set_state(self, stream_id: str, state: str) -> None:
        """Set the stream state; record started_at when going LIVE."""
        if state not in _VALID_STATES:
            raise StreamError("invalid stream state")

        def _setter(info: StreamInfo) -> None:
            if info.state == state:
                return
            now = datetime.now(timezone.utc)
            info.state = state
            if state == StreamState.LIVE:
                info.started_at = now
            else:
                info.started_at = None
            info.last_activity_at = now

        self.update(stream_id, _setter)

    def increment_viewers(self, stream_id: str) -> None:
        self.update(stream_id, lambda info: setattr(info, "viewers", info.viewers + 1))

    def decrement_viewers(self, stream_id: str) -> None:
        def _dec(info: StreamInfo) -> None:
            if info.viewers > 0:
                info.viewers -= 1
            info.last_activity_at = datetime.now(timezone.utc)

        self.update(stream_id, _dec)

    def list(self) -> list[StreamInfo]:
        """Return clones of all registered streams, sorted by ID."""
        with self._lock:
            result = [info.clone() for info in self._streams.values()]
        result.sort(key=lambda i: i.id)
        return result

    def delete(self, stream_id: str) -> None:
        """Delete a stream; refuses if it is active or has viewers."""
        with self._lock:
            if stream_id not in self._streams:
                raise StreamError("stream not found")
            info = self._streams[stream_id]
            if (
                info.viewers > 0
                or info.state == StreamState.LIVE
                or info.state == StreamState.RECORDING
            ):
                raise StreamError("stream is active")
            del self._streams[stream_id]

    def count(self) -> int:
        with self._lock:
            return len(self._streams)

    def live_count(self) -> int:
        with self._lock:
            return sum(1 for i in self._streams.values() if i.state == StreamState.LIVE)

    def cleanup_stale(self) -> int:
        """Remove idle streams older than the TTL.  Returns count removed."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self._stream_ttl)
        removed: list[str] = []
        with self._lock:
            for stream_id, info in list(self._streams.items()):
                if (
                    info.viewers > 0
                    or info.state == StreamState.LIVE
                    or info.state == StreamState.RECORDING
                ):
                    continue
                last = info.last_activity_at or info.created_at
                if last is not None and last < cutoff:
                    del self._streams[stream_id]
                    removed.append(stream_id)
        return len(removed)
