from __future__ import annotations

import itertools
import json
import logging
import os
import subprocess
import tempfile
import threading
import time

from .library import find_ytdlp
from .paths import resolve_executable

_ids = itertools.count()
log = logging.getLogger("autodj")
POLL = 0.5  # seconds between hang checks while a track with a known length plays
_WHY = ("error", "fail", "not found", "unable", "[ytdl_hook]", "cannot", "no such")
# Position cache TTL: the GUI polls position() every POLL seconds; caching the
# mpv-reported position for one poll cycle avoids opening a new IPC connection
# on every poll while keeping the progress bar imperceptibly current.
_POS_CACHE_TTL = 0.5


def _is_windows() -> bool:
    """Return whether the host uses Windows-specific process and IPC behavior."""
    return os.name == "nt"


def failure_reasons(log_text: str, keep: int = 4) -> list[str]:
    """The last few lines of an mpv log that explain why playback failed."""
    lines = [ln.strip() for ln in log_text.splitlines() if any(w in ln.lower() for w in _WHY)]
    return lines[-keep:]


class MpvPlayer:
    """One mpv process per track. mpv plays local files and YouTube (via yt-dlp) alike."""

    def __init__(self, cfg, stop_evt: threading.Event | None = None):
        self.cfg = cfg
        self.stop_evt = stop_evt
        self.proc: subprocess.Popen | None = None
        self._ipc: str | None = None
        self.skipped = False
        self._lock = threading.Lock()
        self._paused_since: float | None = (
            None  # monotonic time of the current pause (hang timer excludes pauses)
        )
        self._paused_total = 0.0
        self._pos_cache: tuple[float, float] | None = None  # (position, monotonic time)

    def available(self) -> bool:
        return bool(resolve_executable(self.cfg.mpv_path))

    def _base(self) -> list[str]:
        mpv_executable = resolve_executable(self.cfg.mpv_path) or self.cfg.mpv_path
        a = [
            mpv_executable,
            "--no-video",
            "--force-window=no",
            "--no-terminal",
            "--really-quiet",
        ]
        if self.cfg.audio_device:
            a.append(f"--audio-device={self.cfg.audio_device}")
        if getattr(self.cfg, "audio_normalize", False):
            # Dynamic audio loudness normalization via FFmpeg dynaudnorm filter
            a.append("--af=dynaudnorm=f=75:g=15:p=0.95")
        return a

    def _fade_volume(self, start_vol: int, target_vol: int, duration_sec: float):
        """Asynchronously ramps volume over duration_sec."""
        steps = max(int(duration_sec / 0.1), 1)
        step_duration = duration_sec / steps
        vol_delta = (target_vol - start_vol) / steps
        current = float(start_vol)
        for _ in range(steps):
            if self.skipped or self.proc is None:
                break
            current += vol_delta
            self.set_volume(round(current))
            time.sleep(step_duration)
        if not self.skipped and self.proc is not None:
            self.set_volume(target_vol)

    def _ipc_log_paths(self, n: int) -> tuple[str, str]:
        """IPC server address and mpv log file for playback job *n*."""
        if _is_windows():
            ipc = rf"\\.\pipe\camfrog-autodj-{os.getpid()}-{n}"
        else:
            ipc = os.path.join(tempfile.gettempdir(), f"camfrog-autodj-{os.getpid()}-{n}.sock")
        logf = os.path.join(tempfile.gettempdir(), f"camfrog-autodj-mpv-{os.getpid()}-{n}.log")
        return ipc, logf

    def _wait_for_mpv_end(
        self, p: subprocess.Popen, started: float, limit: float | None
    ) -> tuple[int | None, bool]:
        """Wait for mpv to exit; return (returncode, hung). hung means the grace limit was exceeded.

        For live streams (limit=None), we still poll at POLL interval to allow cooperative
        cancellation via stop_evt, but we don't enforce a hard timeout since live duration
        is unknown. The caller is responsible for managing overall track lifecycle.
        """
        rc, hung = None, False
        while rc is None:
            try:
                # Always use POLL timeout to allow periodic checks; when limit is None
                # (live stream), we don't treat timeout as "hung" but just continue waiting.
                rc = p.wait(timeout=POLL)
            except subprocess.TimeoutExpired:
                # Check for cooperative cancellation
                if self.stop_evt is not None and self.stop_evt.is_set():
                    log.debug("mpv wait cancelled via stop_evt")
                    break
                if limit is not None and self._played(started) >= limit:
                    hung = True
                    break
                # For live streams (limit=None), continue waiting - no hung detection
        return rc, hung

    def play(self, source: str, volume: int, duration: float | None = None) -> bool:
        """Play one track to its end; True = it played (or was skipped), False = it failed or hung.

        mpv_timeout is a *grace* period on top of the track's length, never a cap on the length itself
        (it used to be a flat cap, which cut every song longer than the timeout). It only applies when the
        duration is known; time spent paused does not count. Unknown duration (live) = no limit."""
        n = next(_ids)
        ipc, logf = self._ipc_log_paths(n)
        fade_in = (
            getattr(self.cfg, "audio_fade", False)
            and getattr(self.cfg, "audio_fade_in_sec", 0.0) > 0
        )
        init_vol = 0 if fade_in else volume
        cmd = self._base() + [
            "--ytdl-format=bestaudio/best",
            f"--input-ipc-server={ipc}",
            f"--log-file={logf}",
            f"--volume={init_vol}",
        ]
        ytdlp = find_ytdlp(getattr(self.cfg, "ytdlp_path", ""), self.cfg.mpv_path)
        if ytdlp:  # mpv's youtube hook must use the same yt-dlp our title lookups use; its own default search only looks on PATH
            cmd.append(f"--script-opts=ytdl_hook-ytdl_path={ytdlp}")
        cmd += ["--", source]
        kw: dict = {}
        if _is_windows():
            kw["creationflags"] = 0x08000000  # CREATE_NO_WINDOW: no console flash in GUI mode
        with self._lock:
            self.skipped = False
            self._paused_since, self._paused_total = None, 0.0
            self._ipc = ipc
            self._pos_cache = None
            self.proc = p = subprocess.Popen(cmd, **kw)
        if fade_in:
            threading.Thread(
                target=self._fade_volume,
                args=(0, volume, self.cfg.audio_fade_in_sec),
                daemon=True,
                name="autodj-fade-in",
            ).start()
        limit = (
            float(duration) + float(self.cfg.mpv_timeout or 0.0) if duration is not None else None
        )
        started = time.monotonic()
        rc, hung = self._wait_for_mpv_end(p, started, limit)
        if hung:
            log.warning(
                "mpv still running %.0fs after the expected end of %s: terminating",
                self.cfg.mpv_timeout,
                source,
            )
            with self._lock:
                self.skipped = True
                p.terminate()
            try:
                rc = p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                log.warning("mpv did not exit after terminate; killing")
                with self._lock:
                    p.kill()
                rc = p.wait()
            ok = False
        with self._lock:
            self.proc = None
            self._ipc = None
            if not hung:
                ok = rc == 0 or self.skipped
        assert rc is not None
        self._report(ok, rc, source, logf)
        return ok

    def _played(self, started: float) -> float:
        """Seconds of actual playing since `started` (pauses excluded)."""
        with self._lock:
            now = time.monotonic()
            paused = self._paused_total + (now - self._paused_since if self._paused_since else 0.0)
        return now - started - paused

    @staticmethod
    def _report(ok: bool, rc: int, source: str, logf: str):
        """On failure put mpv's own explanation in our log (mpv itself is run silent); always clean up."""
        try:
            if not ok:
                with open(logf, encoding="utf-8", errors="replace") as f:
                    why = failure_reasons(f.read())
                log.warning(
                    "mpv exited with code %s for %s%s",
                    rc,
                    source,
                    "".join("\n    " + ln for ln in why)
                    if why
                    else " (no error line in mpv's log)",
                )
        except OSError:
            log.warning(
                "mpv exited with code %s for %s (no log written: is mpv_path correct?)",
                rc,
                source,
            )
        finally:
            try:
                os.remove(logf)
            except OSError:
                pass

    def stop(self):
        fade_out = (
            getattr(self.cfg, "audio_fade", False)
            and getattr(self.cfg, "audio_fade_out_sec", 0.0) > 0
        )
        if fade_out and self._ipc:
            # Quick fade out before terminating
            try:
                self._fade_volume(
                    getattr(self.cfg, "volume", 100),
                    0,
                    min(self.cfg.audio_fade_out_sec, 0.8),
                )
            except (OSError, ValueError):
                pass  # fade-out is best-effort; termination proceeds regardless
        with self._lock:
            p = self.proc
            self._pos_cache = None
            if p and p.poll() is None:
                self.skipped = True
                p.terminate()

    def _cmd(self, *cmd) -> bool:
        """Send a command to mpv via IPC (fire-and-forget). Returns True if sent."""
        ipc = self._ipc
        if not ipc:
            return False
        data = (json.dumps({"command": list(cmd)}) + "\n").encode()
        try:
            if _is_windows():
                with open(ipc, "r+b", buffering=0) as f:
                    f.write(data)
            else:
                import socket

                with socket.socket(socket.AF_UNIX) as s:  # type: ignore[attr-defined]  # AF_UNIX only on non-Windows
                    s.connect(ipc)
                    s.sendall(data)
            return True
        except OSError:
            return False

    def _cmd_get(self, *cmd) -> float | None:
        """Send a command to mpv via IPC and read the JSON response. Returns the property value or None on failure.

        Uses a 2-second timeout for reading the response to avoid hanging indefinitely
        if mpv doesn't respond or the IPC pipe/socket is in a bad state.
        """
        ipc = self._ipc
        if not ipc:
            return None
        request_id = next(_ids)
        data = (json.dumps({"command": list(cmd), "request_id": request_id}) + "\n").encode()
        try:
            if _is_windows():
                response = self._ipc_read_windows(ipc, data)
            else:
                response = self._ipc_read_unix(ipc, data)
            if not response:
                return None
            # Parse JSON response
            resp = json.loads(response.decode("utf-8", errors="replace"))
            if resp.get("request_id") == request_id and "data" in resp:
                return resp["data"]
        except (OSError, json.JSONDecodeError, StopIteration, TimeoutError):
            return None
        return None

    def _ipc_read_windows(self, ipc: str, data: bytes, timeout: float = 2.0) -> bytes | None:
        """Read IPC response from Windows named pipe with timeout."""
        import time

        start = time.monotonic()
        try:
            with open(ipc, "r+b", buffering=0) as f:
                f.write(data)
                response = b""
                while b"\n" not in response:
                    if time.monotonic() - start > timeout:
                        log.debug("_cmd_get timed out reading from IPC pipe")
                        return None
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    response += chunk
                return response
        except OSError:
            return None

    def _ipc_read_unix(self, ipc: str, data: bytes, timeout: float = 2.0) -> bytes | None:
        """Read IPC response from Unix socket with timeout."""
        import socket
        import time

        start = time.monotonic()
        try:
            with socket.socket(socket.AF_UNIX) as s:  # type: ignore[attr-defined]  # AF_UNIX only on non-Windows
                s.settimeout(timeout)
                s.connect(ipc)
                s.sendall(data)
                response = b""
                while b"\n" not in response:
                    if time.monotonic() - start > timeout:
                        log.debug("_cmd_get timed out reading from IPC socket")
                        return None
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                return response
        except (OSError, TimeoutError):
            return None

    def _invalidate_pos_cache(self) -> None:
        """Drop the cached mpv position so the next get_time_pos() re-queries IPC."""
        with self._lock:
            self._pos_cache = None

    def get_time_pos(self) -> float | None:
        """Get the current playback position in seconds from mpv via IPC.

        The last reported position is cached for _POS_CACHE_TTL seconds so the
        GUI's frequent position polls (every 500 ms) do not open a new IPC
        connection (named pipe on Windows, Unix socket on Linux) on every poll.
        Returns None if unavailable.
        """
        now = time.monotonic()
        cached: tuple[float, float] | None = None
        with self._lock:
            cached = self._pos_cache
        if cached is not None:
            cpos, ts = cached
            if now - ts <= _POS_CACHE_TTL:
                return cpos
        pos: float | None = self._cmd_get("get_property", "time-pos")
        if pos is not None:
            with self._lock:
                self._pos_cache = (pos, time.monotonic())
        return pos

    def seek(self, seconds: float) -> bool:
        """Seek to an absolute position (seconds) in the current track via mpv IPC.
        Returns True if the seek command was sent successfully."""
        ok = self._cmd("seek", seconds, "absolute")
        self._invalidate_pos_cache()
        return ok

    def set_pause(self, v: bool) -> bool:
        return self._cmd("set_property", "pause", v)

    def set_volume(self, v: int) -> bool:
        return self._cmd("set_property", "volume", v)

    def play_file(self, path: str, duck_volume: int | None = None):
        """Play a single file (e.g. TTS WAV) and set up IPC so volume control works during playback.

        Args:
            path: Path to the audio file to play.
            duck_volume: Optional volume level (0-100) to set after IPC is established
                but before playback starts. Used for TTS ducking.
        """
        # Set up IPC so set_volume() (ducking) works during TTS playback
        n = next(_ids)
        ipc, logf = self._ipc_log_paths(n)
        kw: dict = {}
        if _is_windows():
            kw["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        kw["timeout"] = 30
        cmd = self._base() + [
            "--volume=100",
            f"--input-ipc-server={ipc}",
            f"--log-file={logf}",
            "--",
            path,
        ]
        with self._lock:
            self.skipped = False
            self._paused_since, self._paused_total = None, 0.0
            self._ipc = ipc
            self._pos_cache = None
        # Apply duck volume immediately after IPC is established, before playback starts
        if duck_volume is not None:
            self.set_volume(duck_volume)
        try:
            subprocess.run(cmd, check=False, **kw)
        except subprocess.TimeoutExpired:
            log.warning("play_file timed out")
        finally:
            with self._lock:
                self.proc = None
                self._ipc = None
            try:
                os.remove(logf)
            except OSError:
                pass
