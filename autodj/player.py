from __future__ import annotations

import itertools
import json
import logging
import os

# security review: subprocess only with fixed argv lists, never shell=True
import subprocess  # nosec B404
import tempfile
import threading
import time

from .library import find_ytdlp
from .paths import resolve_executable
from .winjob import kill_with_parent

_ids = itertools.count()
log = logging.getLogger("autodj")
POLL = 0.5  # seconds between hang checks while a track with a known length plays
_WHY = ("error", "fail", "not found", "unable", "[ytdl_hook]", "cannot", "no such")
# Position cache TTL: the GUI polls position() every POLL seconds; caching the
# mpv-reported position for one poll cycle avoids opening a new IPC connection
# on every poll while keeping the progress bar imperceptibly current.
_POS_CACHE_TTL = 0.5
# A track that is still playing when its grace limit runs out (yt-dlp resolves the
# URL for several seconds before audio starts, and streams buffer) gets this many
# extensions of "remaining time + grace" before it is treated as hung.
MAX_OVERRUN_EXTENSIONS = 3
_OVERRUN_IPC_TIMEOUT = 2.0  # player thread, not the Tk thread: a slower mpv may answer
_CMD_IPC_TIMEOUT = 0.5  # pause / volume / seek: wait this long for a free pipe instance


def _is_windows() -> bool:
    """Return whether the host uses Windows-specific process and IPC behavior."""
    return os.name == "nt"


_MISSING = object()


def _ipc_reply(buf: bytes, request_id: int) -> object:
    """Return the ``data`` of the reply to *request_id* in *buf*, else ``_MISSING``.

    mpv pushes asynchronous event lines (``{"event": ...}``) to every IPC
    client, so a reply can arrive after one or more events in the same read.
    Parsing the whole buffer as one JSON document failed ("Extra data") and
    reported the position/property as unavailable.
    """
    for raw in buf.split(b"\n"):
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw.decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            continue  # a partial trailing line: wait for more bytes
        if isinstance(msg, dict) and msg.get("request_id") == request_id:
            return msg.get("data") if msg.get("error", "success") == "success" else None
    return _MISSING


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
        return bool(resolve_executable(self.cfg.mpv_path, only_exe=True))

    def _mpv_executable(self) -> str:
        """Return the mpv binary to launch -- always ``mpv.exe``, never ``mpv.com``."""
        resolved = resolve_executable(self.cfg.mpv_path, only_exe=True)
        if resolved:
            return resolved
        # No file on disk: keep the historical fallback for diagnostics/tests,
        # but still never hand a .com shim (or a bare Windows command) to mpv.
        raw = (self.cfg.mpv_path or "mpv").strip()
        if os.name != "nt":
            return raw
        if "/" in raw or "\\" in raw:
            return raw[:-4] + ".exe" if raw.lower().endswith(".com") else raw
        return raw if raw.lower().endswith(".exe") else raw + ".exe"

    def _base(self) -> list[str]:
        mpv_executable = self._mpv_executable()
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
        """Wait for mpv to exit; return (returncode, hung). hung means the grace limit was exceeded."""
        rc, hung = None, False
        while rc is None:
            try:
                rc = p.wait(timeout=POLL if limit is not None else None)
            except subprocess.TimeoutExpired:
                if limit is not None and self._played(started) >= limit:
                    hung = True
                    break
        return rc, hung

    def _wait_with_overrun(
        self,
        p: subprocess.Popen,
        source: str,
        started: float,
        limit: float | None,
        duration: float | None,
    ) -> tuple[int | None, bool]:
        """Wait for mpv; while it is still playing past the limit, extend it (bounded)."""
        rc, hung = self._wait_for_mpv_end(p, started, limit)
        extensions = 0
        while hung:
            left = (
                self._remaining_if_playing(duration)
                if extensions < MAX_OVERRUN_EXTENSIONS
                else None
            )
            # mpv may have finished on its own during the 1 s position probe (an
            # empty second read): that is a normal exit, never a hang.
            exited = p.poll()
            if isinstance(exited, int):
                return exited, False
            if left is None:
                break
            extensions += 1
            log.info(
                "mpv still playing %s with %.0f s left (late start or buffering): waiting",
                source,
                left,
            )
            limit = self._played(started) + left + float(self.cfg.mpv_timeout or 0.0)
            rc, hung = self._wait_for_mpv_end(p, started, limit)
        return rc, hung

    def _query(self, prop: str) -> object:
        """One mpv property over IPC with the overrun timeout (None if unavailable)."""
        self._invalidate_pos_cache()
        return self._cmd_get("get_property", prop, timeout=_OVERRUN_IPC_TIMEOUT)

    def _remaining_if_playing(self, duration: float | None) -> float | None:
        """Seconds left when mpv is still playing short of the end, else None.

        Two position reads one second apart: an advancing position means the song
        is playing (it started late or buffered), not hung.
        """
        if duration is None:
            return None
        first = self._query("time-pos")
        if not isinstance(first, (int, float)) or isinstance(first, bool):
            return None
        time.sleep(1.0)
        second = self._query("time-pos")
        if not isinstance(second, (int, float)) or isinstance(second, bool) or second <= first:
            return None
        left = float(duration) - float(second)
        return left if left > 2.0 else None

    def _stop_after_hang(
        self, p: subprocess.Popen, source: str, duration: float | None
    ) -> tuple[int, bool]:
        """Stop an mpv that outlived its grace limit; report if it actually finished."""
        log.warning(
            "mpv still running %.0fs after the expected end of %s: checking position",
            self.cfg.mpv_timeout,
            source,
        )
        # Wrong/short metadata duration or a stalled end-of-stream can keep mpv
        # alive past the limit even though the song played to the end.  Ask mpv
        # with a real timeout (the cached GUI query uses 0.15 s and returned
        # nothing from a busy mpv, so finished songs were logged as FAILED).
        raw = self._query("time-pos")
        pos = float(raw) if isinstance(raw, (int, float)) and not isinstance(raw, bool) else None
        eof = self._query("eof-reached")  # True / False, or None when mpv does not answer
        reached_end = eof is True or (
            pos is not None and duration is not None and pos >= max(0.0, float(duration) - 2.0)
        )
        if reached_end:
            log.info("mpv reached the end of %s before the hang timeout: completed", source)
        elif pos is None and eof is None:
            # No answer within 2 s: mpv itself is hung; that stays a failure.
            log.info("mpv did not answer for %s: treating it as hung", source)
        else:
            log.info(
                "mpv stopped at %s of %s s for %s (eof-reached=%s)",
                "unknown" if pos is None else f"{pos:.0f}",
                "unknown" if duration is None else f"{float(duration):.0f}",
                source,
                eof,
            )
        with self._lock:
            if not reached_end:
                self.skipped = True
            p.terminate()
        try:
            rc = p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            log.warning("mpv did not exit after terminate; killing")
            with self._lock:
                p.kill()
            rc = p.wait()
        return rc, reached_end

    def play(self, source: str, volume: int, duration: float | None = None) -> bool:
        """Play one track to its end; True = it played (or was skipped), False = it failed or hung.

        mpv_timeout is a *grace* period on top of the track's length, never a cap on the length itself
        (it used to be a flat cap, which cut every song longer than the timeout). It only applies when the
        duration is known; time spent paused does not count. Unknown duration (live) = no limit.
        """
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
            if self.stop_evt is not None and self.stop_evt.is_set():
                # Shutdown raced with the player loop: never start an mpv that
                # nobody will stop (it kept playing after AutoDJ exited).
                return True
            self.skipped = False
            self._paused_since, self._paused_total = None, 0.0
            self._ipc = ipc
            self._pos_cache = None
            # security review: argv list without shell; executable is sys.executable or a resolved, configured tool path
            self.proc = p = subprocess.Popen(cmd, **kw)  # nosec B603
            kill_with_parent(p)  # mpv dies with AutoDJ, even on End task / crash
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
        rc, hung = self._wait_with_overrun(p, source, started, limit, duration)
        reached_end = False
        if hung:
            rc, reached_end = self._stop_after_hang(p, source, duration)
            ok = reached_end
        # Computed before taking _lock: _played() takes it itself.
        played_to_end = (
            duration is not None and duration > 0 and self._played(started) >= duration - 5.0
        )
        with self._lock:
            self.proc = None
            self._ipc = None
            if not hung:
                ok = rc == 0 or self.skipped
                if not ok and played_to_end:
                    # Streams often end with mpv exit code 1 (a dropped connection
                    # or hook error at EOF) after the whole song played: that is a
                    # completed track, not a failure to announce.
                    log.info(
                        "mpv exited with code %s after playing %s to the end: completed",
                        rc,
                        source,
                    )
                    ok = True
        if rc is None:  # defensive: never pass None to _report (asserts vanish under -O)
            rc = -1
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
                    (
                        "".join("\n    " + ln for ln in why)
                        if why
                        else " (no error line in mpv's log)"
                    ),
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
            self._ipc = None  # Clear IPC so no further commands target dead process
            running = p is not None and p.poll() is None
            if p is not None and running:
                self.skipped = True
                p.terminate()
        # Wait *outside* the lock: holding it here blocked the GUI's 500 ms
        # position poll (get_time_pos) for up to 10 s on a stuck mpv.
        if p is not None and running:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                log.warning("mpv did not exit after terminate; killing")
                p.kill()
                p.wait()

    def _cmd(self, *cmd) -> bool:
        """Send a command to mpv via IPC (fire-and-forget). Returns True if sent."""
        ipc = self._ipc
        if not ipc:
            return False
        data = (json.dumps({"command": list(cmd)}) + "\n").encode()
        try:
            if _is_windows():
                from .winpipe import request

                # waits for a free pipe instance (the GUI's position poll may hold one)
                request(ipc, data, _CMD_IPC_TIMEOUT, lambda _buf: True)
            else:
                import socket

                with socket.socket(socket.AF_UNIX) as s:  # type: ignore[attr-defined]  # AF_UNIX only on non-Windows
                    s.connect(ipc)
                    s.sendall(data)
            return True
        except OSError:
            return False

    def _cmd_get(self, *cmd, timeout: float = 2.0) -> float | None:
        """Send a command to mpv via IPC and read the JSON response. Returns the property value or None on failure.

        ``timeout`` is caller-controlled: GUI position polls use a short one so
        a stuck mpv can never freeze the Tk main thread for seconds.
        """
        ipc = self._ipc
        if not ipc:
            return None
        request_id = next(_ids)
        data = (json.dumps({"command": list(cmd), "request_id": request_id}) + "\n").encode()
        try:
            if _is_windows():
                response = self._ipc_read_windows(ipc, data, timeout, request_id)
            else:
                response = self._ipc_read_unix(ipc, data, timeout, request_id)
        except (OSError, TimeoutError):
            return None
        if not response:
            return None
        value = _ipc_reply(response, request_id)
        return None if value is _MISSING else value  # type: ignore[return-value]

    def _ipc_read_windows(
        self, ipc: str, data: bytes, timeout: float = 2.0, request_id: int | None = None
    ) -> bytes | None:
        """Read the IPC reply from a Windows named pipe; *timeout* bounds connect + read."""
        from .winpipe import request

        try:
            response = request(ipc, data, timeout, lambda buf: self._have_reply(buf, request_id))
        except OSError as ex:
            log.debug("mpv IPC request failed: %s", ex)
            return None
        if response is None:
            log.debug("_cmd_get timed out reading from IPC pipe")
        return response

    def _ipc_read_unix(
        self, ipc: str, data: bytes, timeout: float = 2.0, request_id: int | None = None
    ) -> bytes | None:
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
                while not self._have_reply(response, request_id):
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

    @staticmethod
    def _have_reply(buf: bytes, request_id: int | None) -> bool:
        """Stop reading once the reply to *request_id* (or, without one, any line) arrived."""
        if request_id is None:
            return b"\n" in buf
        return b"\n" in buf and _ipc_reply(buf, request_id) is not _MISSING

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
        # Short timeout: this is called from the Tk main thread by the GUI
        # poller; a 2 s IPC stall here used to freeze the whole window.
        pos: float | None = self._cmd_get("get_property", "time-pos", timeout=0.15)
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

    def play_file(
        self,
        path: str,
        duck_volume: int | None = None,
        restore_volume: int | None = None,
        timeout: float = 120.0,
    ):
        """Play a single file (e.g. TTS WAV) and set up IPC so volume control works during playback.

        Args:
            path: Path to the audio file to play.
            duck_volume: Optional volume level (0-100) to set after IPC is established
                but before playback starts. Used for TTS ducking.
            restore_volume: Optional volume level (0-100) to restore after playback completes.
                If provided, the volume is restored atomically after the file finishes playing,
                ensuring IPC is still available. This avoids a race where the caller restores
                volume after play_file() returns but IPC has already been cleared.
            timeout: Maximum time in seconds to wait for playback to complete.
                Default 120s to accommodate TTS synthesis (up to 60s) + playback.
        """
        kw: dict = {}
        if _is_windows():
            kw["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        # Duck the *music* mpv (its IPC stays live: the clip is a separate process),
        # play the clip, then restore in `finally` — the duck/restore arguments used
        # to be ignored, so TTS was spoken over full-volume music.
        ducked = duck_volume is not None and self.set_volume(int(duck_volume))
        try:
            # security review: argv list without shell; resolved mpv path
            clip = subprocess.Popen(  # nosec B603
                self._base() + ["--volume=100", "--", path], **kw
            )
            kill_with_parent(clip)  # the TTS mpv dies with AutoDJ too
            try:
                clip.wait(timeout=max(1.0, float(timeout)))  # a broken WAV must not block forever
            except subprocess.TimeoutExpired:
                clip.kill()
                clip.wait()
                log.warning("TTS clip did not finish within %.0fs: stopped", timeout)
        finally:
            if ducked and restore_volume is not None:
                # security review: argv list without shell; executable is sys.executable or a resolved, configured tool path
                self.set_volume(int(restore_volume))
