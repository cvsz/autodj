"""FFmpeg stream recorder manager.

Ported from cvsz/streamdbc internal/recorder/manager.go.

Records an input stream (RTMP, RTSP, HTTP(S), SRT, etc.) to an MP4 file using
FFmpeg with stream-copy (no re-encode).  Each stream can have at most one
active recording.  Recordings are tracked with lifecycle states and a capped
history of superseded recordings is retained for post-mortem inspection.

AutoDJ uses this to archive broadcasts from any platform (Camfrog, YouTube,
TikTok, Facebook) for later review or rebroadcast.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess  # nosec B404
import threading
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from .stream_id import validate_stream_id


class RecorderError(Exception):
    """Recorder manager error."""


class RecorderStoppedError(RecorderError):
    """The recorder manager has been stopped."""


_STATE_STARTING = "starting"
_STATE_RECORDING = "recording"
_STATE_STOPPED = "stopped"
_STATE_FAILED = "failed"
_STATE_CANCELLED = "cancelled"

_MAX_ACTIVE_RECORDINGS = 64
_MAX_RECORDING_HISTORY = 128
_MAX_FFMPEG_LOG = 64 * 1024


_ALLOWED_SCHEMES = frozenset({"http", "https", "rtmp", "rtmps", "rtsp", "rtsps", "srt"})


@dataclass
class Recording:
    """Snapshot of a recording's current state."""

    id: str
    stream_id: str
    output_path: str
    start_time: datetime
    duration: float = 0.0
    size: int = 0
    state: str = _STATE_STARTING

    def clone(self) -> "Recording":
        return Recording(
            id=self.id,
            stream_id=self.stream_id,
            output_path=self.output_path,
            start_time=self.start_time,
            duration=self.duration,
            size=self.size,
            state=self.state,
        )


class _LimitedBuffer:
    """Bounded byte buffer for capturing limited FFmpeg stderr output."""

    def __init__(self, limit: int = _MAX_FFMPEG_LOG) -> None:
        self._lock = threading.Lock()
        self._data: bytearray = bytearray()
        self._limit = limit

    def write(self, data: bytes) -> int:
        with self._lock:
            original = len(data)
            remaining = self._limit - len(self._data)
            if remaining > 0:
                if len(data) > remaining:
                    data = data[:remaining]
                self._data.extend(data)
            return original

    def string(self) -> str:
        with self._lock:
            return bytes(self._data).decode("utf-8", errors="replace")


class RecorderManager:
    """Manages FFmpeg-based stream recordings."""

    def __init__(
        self,
        recordings_path: str,
        ffmpeg_path: str = "ffmpeg",
        max_active: int = _MAX_ACTIVE_RECORDINGS,
    ) -> None:
        if not recordings_path or not recordings_path.strip():
            raise RecorderError("recordings path is required")
        if not ffmpeg_path:
            ffmpeg_path = "ffmpeg"

        # Resolve ffmpeg executable.
        resolved = self._which(ffmpeg_path)
        if resolved is None:
            raise RecorderError(f"ffmpeg not found at {ffmpeg_path!r}")

        root = Path(recordings_path).expanduser().resolve()
        if root.is_symlink() or not root.is_dir():
            try:
                root.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise RecorderError(f"failed to create recordings directory: {exc}") from exc
            if root.is_symlink() or not root.is_dir():
                raise RecorderError("recordings path must be a regular directory")

        self._config_path = str(root)
        self._ffmpeg_path = resolved
        self._max_active = max_active
        self._logger = None  # placeholder; callers can inject logging
        self._recordings: dict[str, Recording] = {}
        self._history: list[Recording] = []
        self._lock = threading.RLock()
        self._stopped = False
        self._cancel_event = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start_recording(
        self,
        stream_id: str,
        input_url: str,
        on_complete: Optional[Callable[[str, Optional[Exception]], None]] = None,
    ) -> None:
        """Start recording *input_url* for *stream_id* to an MP4 file."""
        validate_stream_id(stream_id)
        self._validate_input_url(input_url)

        with self._lock:
            if self._stopped or self._cancel_event.is_set():
                raise RecorderStoppedError("recorder is stopped")
            existing = self._recordings.get(stream_id)
            if existing is not None and self._is_active(existing.state):
                raise RecorderError(f"recording already in progress for stream {stream_id}")
            active = sum(1 for rec in self._recordings.values() if self._is_active(rec.state))
            if active >= self._max_active:
                raise RecorderError(f"recording limit of {self._max_active} reached")

            now = datetime.now(timezone.utc)
            filename = f"{stream_id}_{now.strftime('%Y%m%d_%H%M%S.%f')}.mp4"
            output_path = str(root / filename) if (root := Path(self._config_path)) else filename
            rec = Recording(
                id=f"{stream_id}_{int(now.timestamp() * 1_000_000_000)}",
                stream_id=stream_id,
                output_path=output_path,
                start_time=now,
                state=_STATE_STARTING,
            )
            cmd = subprocess.Popen(  # nosec B603
                [
                    self._ffmpeg_path,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-nostdin",
                    "-i",
                    input_url,
                    "-c:v",
                    "copy",
                    "-c:a",
                    "copy",
                    "-f",
                    "mp4",
                    output_path,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            stderr_buf = _LimitedBuffer()
            # Capture stderr in a background thread so Popen.communicate()
            # isn't needed (we wait on the process directly).
            rec._cmd = cmd  # type: ignore[attr-defined]
            rec._stderr_buf = stderr_buf  # type: ignore[attr-defined]
            rec._stop_requested = False  # type: ignore[attr-defined]

            if existing is not None and existing is not rec:
                self._archive_history(existing)
            self._recordings[stream_id] = rec

        thread = threading.Thread(target=self._run_recording, args=(rec, stderr_buf), daemon=True)
        thread.start()

    def stop_recording(self, stream_id: str) -> None:
        """Request graceful termination of a stream recording."""
        with self._lock:
            rec = self._recordings.get(stream_id)
            if rec is None:
                raise RecorderError(f"no recording found for stream {stream_id}")
            if not self._is_active(rec.state):
                return
            rec._stop_requested = True  # type: ignore[attr-defined]
            process = rec._cmd  # type: ignore[attr-defined]

        if process is not None:
            try:
                process.send_signal(signal.SIGINT)
            except OSError:
                pass

    def stop_all(self, timeout: float = 30.0) -> None:
        """Request all recordings to stop and wait for processes to exit."""
        with self._lock:
            self._stopped = True
            processes = []
            for rec in self._recordings.values():
                if self._is_active(rec.state):
                    rec._stop_requested = True  # type: ignore[attr-defined]
                    if rec._cmd is not None:  # type: ignore[attr-defined]
                        processes.append(rec._cmd)  # type: ignore[attr-defined]
            self._cancel_event.set()

        for process in processes:
            with contextlib.suppress(OSError):
                process.send_signal(signal.SIGINT)

        # Wait for recording threads to finish.
        deadline = time.time() + timeout
        while True:
            with self._lock:
                active = any(self._is_active(rec.state) for rec in self._recordings.values())
            if not active:
                return
            if time.time() >= deadline:
                with self._lock:
                    for rec in self._recordings.values():
                        if self._is_active(rec.state) and rec._cmd is not None:  # type: ignore[attr-defined]
                            with contextlib.suppress(OSError):
                                rec._cmd.kill()  # type: ignore[attr-defined]
                return
            time.sleep(0.2)

    def get_recording(self, stream_id: str) -> Optional[Recording]:
        """Return a clone of the recording for *stream_id*, or None."""
        with self._lock:
            rec = self._recordings.get(stream_id)
            if rec is None:
                return None
            return rec.clone()

    def list_recordings(self) -> list[Recording]:
        """Return clones of all tracked recordings plus archived history."""
        with self._lock:
            result = [rec.clone() for rec in self._recordings.values()]
            result.extend(rec.clone() for rec in self._history)
        result.sort(key=lambda r: r.id)
        return result

    def get_stats(self) -> dict:
        """Return recorder statistics."""
        with self._lock:
            active = sum(1 for r in self._recordings.values() if self._is_active(r.state))
            total_duration = 0.0
            total_size = 0
            for r in self._recordings.values():
                total_duration += r.duration
                if self._is_active(r.state):
                    total_duration += (datetime.now(timezone.utc) - r.start_time).total_seconds()
                total_size += r.size
            for r in self._history:
                total_duration += r.duration
                total_size += r.size
            return {
                "active_recordings": active,
                "total_recordings": len(self._recordings) + len(self._history),
                "total_duration": total_duration,
                "total_size_bytes": total_size,
                "output_path": self._config_path,
            }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    @staticmethod
    def _which(executable: str) -> Optional[str]:
        """Locate an executable on PATH (no shell=True)."""
        import shutil

        return shutil.which(executable)

    @staticmethod
    def _validate_input_url(input_url: str) -> None:
        if (
            not input_url
            or input_url != input_url.strip()
            or any(ch in input_url for ch in ("\x00", "\r", "\n", "\t"))
        ):
            raise RecorderError("invalid recording input URL")
        try:
            parsed = urllib.parse.urlparse(input_url)
        except ValueError as exc:
            raise RecorderError("invalid recording input URL") from exc
        if not parsed.scheme or not parsed.hostname:
            raise RecorderError("invalid recording input URL")
        if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
            raise RecorderError("unsupported recording URL scheme")

    @staticmethod
    def _is_active(state: str) -> bool:
        return state in (_STATE_STARTING, _STATE_RECORDING)

    def _archive_history(self, rec: Recording) -> None:
        if rec is None or self._is_active(rec.state):
            return
        self._history.append(rec.clone())
        if len(self._history) > _MAX_RECORDING_HISTORY:
            self._history = self._history[-_MAX_RECORDING_HISTORY:]

    def _run_recording(
        self,
        rec: Recording,
        stderr_buf: _LimitedBuffer,
    ) -> None:
        cmd = rec._cmd  # type: ignore[attr-defined]
        try:
            cmd.start()
        except OSError as exc:
            self._finish_recording(rec, exc, stderr_buf.string())
            return

        with self._lock:
            current = self._recordings.get(rec.stream_id)
            if current is rec:
                rec.state = _STATE_RECORDING
                rec._process = cmd.process  # type: ignore[attr-defined]
            stop_requested = rec._stop_requested  # type: ignore[attr-defined]
            process = rec._process  # type: ignore[attr-defined]

        if stop_requested and process is not None:
            with contextlib.suppress(OSError):
                process.send_signal(signal.SIGINT)

        try:
            cmd.wait()
            process_error: Optional[Exception] = None
        except Exception as exc:  # noqa: BLE001
            process_error = exc

        self._finish_recording(rec, process_error, stderr_buf.string())

    def _finish_recording(  # noqa: C901 - complex state transition logic
        self,
        rec: Recording,
        process_error: Optional[Exception],
        ffmpeg_log: str,
    ) -> None:
        if process_error is None:
            # Validate output file exists and is non-empty.
            try:
                info = os.stat(rec.output_path)
                if not (
                    not os.path.islink(rec.output_path)
                    and os.path.isfile(rec.output_path)
                    and info.st_size > 0
                ):
                    process_error = RecorderError("recording output is empty")
            except OSError:
                process_error = RecorderError("recording output was not created")

        with self._lock:
            current = self._recordings.get(rec.stream_id)
            if current is not rec:
                return
            rec.duration = (datetime.now(timezone.utc) - rec.start_time).total_seconds()
            try:
                info = os.stat(rec.output_path)
                if info.st_size > 0:
                    rec.size = info.st_size
            except OSError:
                pass
            callback = rec.on_complete if hasattr(rec, "on_complete") else None
            rec.on_complete = None  # type: ignore[attr-defined]
            rec.process = None  # type: ignore[attr-defined]
            if process_error is None or rec._stop_requested:  # type: ignore[attr-defined]
                rec.state = _STATE_STOPPED
            elif isinstance(process_error, KeyboardInterrupt) or (
                process_error is not None and self._cancel_event.is_set()
            ):
                rec.state = _STATE_CANCELLED
            else:
                rec.state = _STATE_FAILED
            state = rec.state
            stream_id = rec.stream_id
            output_path = rec.output_path
            duration = rec.duration
            size = rec.size
            self._lock.release()

        if process_error is not None:
            if self._logger:
                self._logger.error(
                    "recording failed",
                    extra={
                        "stream_id": stream_id,
                        "state": state,
                        "error": str(process_error),
                    },
                )
        else:
            if self._logger:
                self._logger.info(
                    "recording completed",
                    extra={
                        "stream_id": stream_id,
                        "output": output_path,
                        "duration": duration,
                        "size": size,
                    },
                )

        if callback is not None:
            try:
                if process_error is not None:
                    callback("", process_error)
                else:
                    callback(output_path, None)
            except Exception:  # noqa: BLE001, S110 - callback must not kill recorder
                if self._logger:
                    self._logger.error(
                        "recording completion callback failed",
                        extra={"stream_id": stream_id},
                    )

    def cleanup_old(self, retention_days: int) -> None:
        """Remove inactive recording files older than *retention_days*."""
        if retention_days <= 0:
            return
        cutoff = time.time() - (retention_days * 86400.0)
        with self._lock:
            active_paths: set[str] = {
                rec.output_path for rec in self._recordings.values() if self._is_active(rec.state)
            }
            root = Path(self._config_path)

        try:
            entries = list(root.iterdir())
        except OSError:
            return

        for entry in entries:
            if entry.is_dir() or entry.is_symlink():
                continue
            try:
                info = entry.stat()
            except OSError:
                continue
            if not info.st_mtime < cutoff:
                continue
            path = str(entry)
            with self._lock:
                if path in active_paths:
                    continue
            try:
                entry.unlink()
                if self._logger:
                    self._logger.info("removed old recording", extra={"path": path})
            except OSError:
                pass
