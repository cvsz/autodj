from __future__ import annotations

import itertools
import json
import logging
import os
import queue
import random
import re
import textwrap
import threading
import time
from collections import deque
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .adapters.base import ChatMessage
from .commands import Router
from .exceptions import (
    ChatAdapterError,
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
    remote_tracks,
    scan_folder,
)
from .messages import tr
from .models import Track
from .player import MpvPlayer
from .playlist import PlaylistStore, load_playlist
from .playqueue import PlayQueue
from .renderer import RenderedMessage, get_renderer
from .textutil import clean_text, norm
from .webhook import WebhookConfig, WebhookServer

log = logging.getLogger("autodj")

MAX_FAIL_ANNOUNCE = (
    3  # consecutive failed tracks announced in the room; after that only the log hears about it
)
MAX_BACKOFF = 30.0  # seconds, ceiling of the pause between consecutive failed tracks
ECHO_TTL = 120.0  # seconds a line we posted is remembered, to recognise it when it comes back from the room

# Failure categories for structured diagnostics
FAIL_RESOLVE = "resolve_failed"  # yt-dlp/search could not resolve the source
FAIL_PLAYBACK = "playback_failed"  # mpv could not play the track
FAIL_HUNG = "playback_hung"  # mpv did not exit within the expected time
FAIL_CRASH = "playback_crashed"  # mpv exited with non-zero code
FAIL_DELIVERY = "chat_delivery_failed"  # chat message could not be delivered
FAIL_CONFIG = "config_error"  # configuration problem

_req_ids = itertools.count()  # global request ID_counter

# Circuit breaker thresholds
_CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5  # consecutive failures before opening
_CIRCUIT_BREAKER_RESET_TIMEOUT = 60.0  # seconds before attempting half-open
_MAX_CONSECUTIVE_SEND_FAILURES = 10  # stop retrying chat sends after this many failures

# Per-nick chat rate limiting (prevents spam flooding)
_CHAT_RATE_LIMIT_WINDOW = 60.0  # seconds
_CHAT_RATE_LIMIT_MAX = 20  # max messages per nick per window


class Engine:
    def __init__(self, cfg, adapter, player=None, index=None, cfg_path=None):
        self.cfg, self.adapter = cfg, adapter
        self.cfg_path = cfg_path
        self.lang = cfg.lang
        self.stop_evt = threading.Event()
        self.player = player or MpvPlayer(cfg, self.stop_evt)
        self.index = index or LocalIndex(cfg.music_dirs)
        pf = getattr(cfg, "playlist_file", "")
        self.playlist = PlaylistStore(pf) if pf else None
        self.queue = PlayQueue(cfg.shuffle)
        self.router = Router(self)
        self.admins = {a.lower() for a in cfg.admins}
        self.current: Track | None = None
        self.volume = cfg.volume
        self.votes: set[str] = set()
        self.paused = False
        self.started_at = 0.0
        self._paused_at: float | None = None
        self._paused_total = 0.0
        self.outbox: queue.Queue[str] = queue.Queue()
        self.chat_log: deque[tuple[str, str]] = deque(maxlen=300)
        self.chat_seq = 0
        self.chat_done = threading.Event()
        self.wake = threading.Event()
        self.exec = ThreadPoolExecutor(
            8
        )  # lookups can take seconds: keep !skip and friends responsive meanwhile
        self.history: deque[Track] = deque(maxlen=20)  # newest first
        self.blocked: set[str] = {b.lower() for b in cfg.blocked_users}
        self.fail_delay = lambda n: min(
            MAX_BACKOFF, 2.0 ** (n - 1)
        )  # n = consecutive failures so far
        self._sent: deque[tuple[float, str]] = deque(maxlen=64)
        self._sent_lock = threading.Lock()
        self._chat_lock = threading.Lock()  # guards chat_log + chat_seq (GUI polls them)
        self._im_reply_cooldowns: dict[str, float] = {}  # user -> last IM reply time
        self._admin_greeting_cooldowns: dict[str, float] = {}  # admin -> last greeting time
        self._welcome_cooldowns: dict[str, float] = {}  # user -> last welcome message time
        self._name_colors: dict[str, str] = {}  # user -> nickname color hex (GUI preview only)
        self.im_log: deque[tuple[str, str]] = deque(maxlen=300)  # IM / private messages
        self.im_seq = 0  # IM message sequence counter for GUI polling
        self._active_room_users: set[str] = set()  # users currently in room (seen in chat)
        self._participant_count: int = 0  # estimated participants (updated from chat)
        self._last_user_request_time: float = 0.0  # monotonic time of last user !play request
        self._autoplay_mode: bool = (
            False  # True when playing from autoplay pool due to idle timeout
        )
        self._speak_lock = (
            threading.Lock()
        )  # one TTS clip at a time: overlapping jobs would un-duck the music early
        self._threads: list[
            threading.Thread
        ] = []  # daemon threads started by start(), joined on shutdown()
        # ---- observability --------------------------------------------------
        self._req_counter = itertools.count()  # per-engine request ID counter
        self._delivery_counter = itertools.count()  # per-engine delivery attempt ID counter
        self._active_requests: dict[str, dict] = {}  # request_id -> {user, arg, start, state}
        self._delivery_attempts: dict[int, dict] = {}  # attempt_id -> {text, stage, confirmed}
        # ---- Circuit breaker state ------------------------------------------------
        self._circuit_breaker_failures: int = 0  # consecutive track failures
        self._circuit_breaker_open_until: float = 0.0  # monotonic time when breaker closes
        self._circuit_breaker_lock: threading.Lock = (
            threading.Lock()
        )  # guards circuit breaker state
        self._send_failure_count: int = 0  # consecutive chat send failures
        self._send_failure_lock: threading.Lock = threading.Lock()  # guards send failure count
        # ---- Per-nick chat rate limiting -----------------------------------------
        self._chat_rate_window: dict[str, deque[float]] = {}  # nick -> deque of message times
        self._chat_rate_lock: threading.Lock = threading.Lock()  # guards rate window dict
        # ---- Health check state --------------------------------------------------
        self._last_health_check: float = 0.0
        self._health_check_interval: float = 30.0  # seconds between auto health checks
        self._backoff_until: float = 0.0  # monotonic time when back-off expires
        # ---- Webhook server -------------------------------------------------------
        self._webhook_server: WebhookServer | None = None
        if getattr(cfg, "webhook_enabled", False):
            webhook_cfg = WebhookConfig(
                enabled=cfg.webhook_enabled,
                port=cfg.webhook_port,
                secret=cfg.webhook_secret,
                host=cfg.webhook_host,
                rate_limit_per_ip=cfg.webhook_rate_limit_per_ip,
            )
            self._webhook_server = WebhookServer(webhook_cfg, self)
        # ---- Plugin system --------------------------------------------------------
        self._plugin_manager: PluginManager | None = None
        plugin_names = getattr(cfg, "plugins", [])
        if plugin_names:
            from .plugins import PluginManager

            self._plugin_manager = PluginManager(self, plugin_names)

    # ---- text -----------------------------------------------------------
    def t(self, key: str, **kw) -> str:
        return tr(self.lang, key, **kw)

    def fmt_now(self, t: Track) -> str:
        try:
            return (
                self.cfg.msg_now.format(**t.fields())
                if self.cfg.msg_now
                else self.t("now_playing", **t.fields())
            )
        except Exception:  # a typo in msg_now must not take down the player-loop thread
            log.exception(
                "bad msg_now template %r: falling back to the built-in text",
                self.cfg.msg_now,
            )
            return self.t("now_playing", **t.fields())

    def fmt_next(self, t: Track) -> str:
        try:
            return (
                self.cfg.msg_next.format(**t.fields())
                if self.cfg.msg_next
                else self.t("up_next", **t.fields())
            )
        except Exception:
            log.exception(
                "bad msg_next template %r: falling back to the built-in text",
                self.cfg.msg_next,
            )
            return self.t("up_next", **t.fields())

    def _is_youtube_playlist(self, url: str) -> bool:
        """Check if the URL is a YouTube playlist URL."""
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
            hostname = parsed.netloc.lower()
            if not any(
                h == hostname or hostname.endswith("." + h)
                for h in ("youtube.com", "youtu.be", "music.youtube.com")
            ):
                return False
            # Check for playlist URL patterns
            if parsed.path == "/playlist":
                return True
            query = parse_qs(parsed.query)
            return "list" in query
        except (ValueError, AttributeError):
            return False

    # ---- chat out -------------------------------------------------------
    def log_chat(self, who: str, text: str):
        with self._chat_lock:
            self.chat_log.append((who, text))
            self.chat_seq += 1
        # Also to the logger (so --log-file / console keeps a trail of every line the bot sent and every
        # line it acted on, even with the GUI closed -- the in-memory chat_log above is lost on restart
        # and was never enough on its own to reconstruct what happened after the fact).
        log.info("chat %s %s: %s", ">>" if who == self.cfg.bot_nick else "<<", who, text)

    def chat_snapshot(self) -> tuple[int, list[tuple[str, str]]]:
        """Thread-safe snapshot of (chat_seq, chat_log) for the GUI poller."""
        with self._chat_lock:
            return self.chat_seq, list(self.chat_log)

    def im_snapshot(self) -> tuple[int, list[tuple[str, str]]]:
        """Thread-safe snapshot of (im_seq, im_log) for the IM viewer GUI poller."""
        with self._chat_lock:
            return self.im_seq, list(self.im_log)

    def say(self, text: str) -> bool:
        """Queue a message for sending to the chat room.

        Returns True if the message was queued, False if chat sends are
        suspended due to repeated failures (circuit breaker).
        """
        text = clean_text(text)
        if not text:
            return True

        # Check send circuit breaker
        if self._is_send_suspended():
            log.warning("Chat send suspended; dropping message: %r", text[:60])
            return False

        # Validate and render using message style (for preview tags, sending is always plain text)
        renderer = get_renderer()
        err = renderer.validate(text)
        if err:
            log.warning("say validation failed: %s", err)
            # Still send but log warning
        rendered: RenderedMessage = renderer.render(self.cfg.message_style, text)
        # Always send plain text - Camfrog does not support rich text
        assert rendered.rich_text is None, "Camfrog protocol does not support rich text"
        self.log_chat(self.cfg.bot_nick, rendered.plain_text)
        for i, chunk in enumerate(
            textwrap.wrap(rendered.plain_text, self.cfg.max_msg_len, break_long_words=True)
        ):
            if i and chunk.startswith(self.cfg.prefix):
                chunk = "… " + chunk  # a wrapped continuation must never look like a command
            self.outbox.put(chunk)
        return True

    # The room shows our own lines back to us under the account's nick, which may differ from bot_nick.
    # Remembering what we posted lets us ignore those echoes instead of treating them as commands.
    def _remember_sent(self, text: str):
        with self._sent_lock:
            self._sent.append((time.monotonic() + ECHO_TTL, norm(text)))

    def _is_echo(self, text: str) -> bool:
        now, want = time.monotonic(), norm(text)
        with self._sent_lock:
            while self._sent and self._sent[0][0] < now:
                self._sent.popleft()
            for i, (_, s) in enumerate(self._sent):
                if s == want:
                    del self._sent[i]
                    return True
        return False

    # ---- observability ------------------------------------------------------

    def _next_request_id(self) -> str:
        return f"req-{next(self._req_counter)}"

    def _next_delivery_id(self) -> int:
        return next(self._delivery_counter)

    def start_request(self, arg: str, user: str) -> str:
        """Record the start of a user request; returns a request ID for correlating logs."""
        req_id = self._next_request_id()
        self._active_requests[req_id] = {
            "user": user,
            "arg": arg,
            "start": time.monotonic(),
            "state": "started",
        }
        log.info(
            "req=%s user=%s arg=%r state=started",
            req_id,
            user,
            arg,
        )
        return req_id

    def update_request(self, req_id: str, state: str, **extra) -> None:
        """Update the state of an active request (resolving, queued, playing, failed, completed)."""
        rec = self._active_requests.get(req_id)
        if rec is None:
            return
        rec["state"] = state
        rec.update(extra)
        elapsed = time.monotonic() - rec["start"]
        log.info(
            "req=%s user=%s state=%s elapsed=%.2fs %s",
            req_id,
            rec["user"],
            state,
            elapsed,
            " ".join(f"{k}={v!r}" for k, v in extra.items()) if extra else "",
        )

    def end_request(self, req_id: str, state: str = "completed") -> None:
        """Mark a request as finished and remove it from active tracking."""
        rec = self._active_requests.pop(req_id, None)
        if rec is None:
            return
        elapsed = time.monotonic() - rec["start"]
        log.info(
            "req=%s user=%s state=%s elapsed=%.2fs",
            req_id,
            rec["user"],
            state,
            elapsed,
        )

    def log_delivery(self, text: str, stage: str, attempt_id: int | None = None) -> int:
        """Record a chat delivery attempt. Returns the attempt ID."""
        if attempt_id is None:
            attempt_id = self._next_delivery_id()
        self._delivery_attempts[attempt_id] = {
            "text": clean_text(text)[:80],  # truncated: never log full private content
            "stage": stage,  # attempted | submitted | confirmed | failed
        }
        log.debug(
            "deliv=%d stage=%s text=%r",
            attempt_id,
            stage,
            self._delivery_attempts[attempt_id]["text"],
        )
        return attempt_id

    def confirm_delivery(self, attempt_id: int) -> None:
        """Mark a delivery attempt as confirmed (the message appeared in the room)."""
        rec = self._delivery_attempts.get(attempt_id)
        if rec is None:
            return
        rec["stage"] = "confirmed"
        log.debug("deliv=%d stage=confirmed", attempt_id)

    def fail_delivery(self, attempt_id: int, category: str = FAIL_DELIVERY) -> None:
        """Mark a delivery attempt as failed with a category."""
        rec = self._delivery_attempts.get(attempt_id)
        if rec is None:
            return
        rec["stage"] = "failed"
        rec["category"] = category
        log.warning(
            "deliv=%d stage=failed category=%s text=%r",
            attempt_id,
            category,
            rec["text"],
        )

    def _log_track(self, t: Track, state: str, req_id: str | None = None) -> None:
        """Structured log for track state transitions."""
        extra = f" req={req_id}" if req_id else ""
        log.info(
            "track=%s state=%s source=%r duration=%s%s",
            id(t),
            state,
            t.source,
            t.dur,
            extra,
        )

    def _sender(self):
        while not self.stop_evt.is_set():
            try:
                m = self.outbox.get(timeout=0.5)
            except queue.Empty:
                continue
            self._remember_sent(m)  # before posting: the echo can show up before send() returns
            attempt_id = self.log_delivery(m, "attempted")
            try:
                self.adapter.send(m)
                self.confirm_delivery(attempt_id)
                self._record_send_success()
                log.info("send ok: %r", m)
            except (OSError, RuntimeError) as ex:
                self.fail_delivery(attempt_id, FAIL_DELIVERY)
                self._record_send_failure()
                log.warning("send failed (%s); retrying once in 2s", ex)
                self.stop_evt.wait(2.0)
                if self.stop_evt.is_set():
                    break
                try:
                    self.adapter.send(m)
                    self.confirm_delivery(attempt_id)
                    self._record_send_success()
                    log.info("send retry ok: %r", m)
                except Exception:
                    self.fail_delivery(attempt_id, FAIL_DELIVERY)
                    self._record_send_failure()
                    log.exception("send retry failed too, dropped: %r", m)
            self.stop_evt.wait(self.cfg.send_interval)  # flood control (wakes up at shutdown)

    # ---- controls -------------------------------------------------------
    def skip(self) -> None:
        self.player.stop()

    def pause(self) -> None:
        if self.current and not self.paused:
            if not self.player.set_pause(True):
                log.warning("pause failed: mpv did not accept the command")
                return
            self.paused, self._paused_at = True, time.monotonic()

    def resume(self) -> None:
        if self.paused:
            if not self.player.set_pause(False):
                log.warning("resume failed: mpv did not accept the command")
                return
            self._paused_total += time.monotonic() - (self._paused_at or time.monotonic())
            self.paused, self._paused_at = False, None

    def voteskip(self, user: str) -> tuple[bool, str]:
        """Register a voteskip from *user* for the current track.

        Returns (passed, message). When the threshold is reached the track
        is skipped immediately.
        """
        if not self.current:
            return False, self.t("nothing_playing")
        self.votes.add(user.lower())
        n = len(self.votes)
        need = self.cfg.voteskip_threshold
        if getattr(self.cfg, "voteskip_dynamic", False):
            participants = getattr(self, "participant_count", 0)
            if participants > 0:
                pct = getattr(self.cfg, "voteskip_dynamic_pct", 30)
                need = max(1, round((participants * pct) / 100.0))
        if n >= need:
            self.skip()
            self.votes.clear()
            return True, self.t("vote_passed", n=n, need=need)
        return False, self.t("vote_progress", n=n, need=need)

    def position(self) -> float:
        if not self.current:
            return 0.0
        # Try to get actual playback position from mpv via IPC
        mpv_pos = self.player.get_time_pos()
        if mpv_pos is not None and mpv_pos >= 0:
            return mpv_pos
        # Fallback to wall-clock calculation (pauses excluded)
        end = self._paused_at or time.monotonic()
        return max(0.0, end - self.started_at - self._paused_total)

    def seek(self, seconds: float) -> bool:
        """Seek to an absolute position (seconds) in the current track.
        Returns True if the seek command was sent successfully."""
        if not self.current:
            return False
        return self.player.seek(seconds)

    def set_volume(self, v: int) -> None:
        self.volume = max(0, min(100, int(v)))
        self.player.set_volume(self.volume)

    def speak(self, text: str) -> None:
        """Text-to-speech into the same output (the Camfrog mic); music is ducked meanwhile."""
        text = clean_text(text)
        if not text:
            return

        def job():
            import tempfile

            from .tts import synth

            wav = os.path.join(tempfile.gettempdir(), f"autodj-tts-{time.time_ns()}.wav")
            with self._speak_lock:
                try:
                    synth(text, wav, self.cfg)
                    # Duck music volume via IPC (play_file applies duck_volume after IPC is established)
                    self.player.play_file(wav, duck_volume=self.cfg.tts_duck)
                except Exception:
                    log.exception("tts failed")
                finally:
                    self.player.set_volume(self.volume)
                    Path(wav).unlink(missing_ok=True)

        self.exec.submit(job)

    def snapshot(self) -> dict:
        with self.queue.lock:
            reqs = list(self.queue.requests)
        return {
            "current": self.current,
            "position": self.position(),
            "paused": self.paused,
            "volume": self.volume,
            "queue": reqs,
            "next": self.queue.peek(),
            "shuffle": self.queue.shuffle,
            "repeat": self.queue.repeat,
            "history": list(self.history),
        }

    # ---- sources --------------------------------------------------------
    def _remote(
        self,
        query: str,
        user: str = "AutoDJ",
        playlist: bool = False,
        search_limit: int | None = None,
        raw_target: bool = False,
    ) -> list[Track]:
        try:
            sl = search_limit if search_limit is not None else self.cfg.search_limit
            return remote_tracks(
                query,
                user,
                playlist=playlist,
                ytdlp_path=self.cfg.ytdlp_path,
                mpv_path=self.cfg.mpv_path,
                search_limit=sl,
                raw_target=raw_target,
                cookies_file=getattr(self.cfg, "youtube_cookies_file", ""),
                cookies_browser=getattr(self.cfg, "youtube_cookies_browser", ""),
                ca_bundle=getattr(self.cfg, "youtube_ca_bundle", ""),
            )
        except YtdlpMissingError as ex:
            log.error(
                "%s", ex
            )  # the details (how to fix it) are for the operator, the room gets a short line
            raise UserError(self.t("yt_missing")) from None

    def recent_requests(self, n: int = 5) -> list[Track]:
        """The newest playlist.json entries that were added by requests (!last)."""
        if not self.playlist:
            return []
        tracks = self.playlist.load()
        fresh = [t for t in tracks if getattr(t, "added", "")]
        return fresh[-n:]

    def resolve(self, arg: str, user: str, admin: bool) -> list[Track]:
        arg = self._normalize_url_arg(arg.strip().strip('"'))
        if not arg:
            raise UserError(self.t("nothing_found"))
        if is_url(arg):
            if not admin and not host_ok(arg, self.cfg.allowed_hosts):
                raise UserError(self.t("host_denied"))
            # Detect YouTube playlist URLs and enable playlist mode automatically
            is_playlist = self._is_youtube_playlist(arg)
            return self._remote(arg, user, playlist=admin or is_playlist)
        if os.path.isabs(arg):
            return self._resolve_local_file(arg, user, admin)
        hit = self.index.find(arg, user)
        return [hit] if hit else self._remote(arg, user)

    def _normalize_url_arg(self, arg: str) -> str:
        """Add https:// scheme to bare YouTube host links pasted without one."""
        if not is_url(arg):
            host = arg.split("/")[0].lower()
            if "." in host and any(
                host == h or host.endswith("." + h) for h in self.cfg.allowed_hosts
            ):
                return "https://" + arg
        return arg

    def _resolve_local_file(self, arg: str, user: str, admin: bool) -> list[Track]:
        p = Path(arg)
        # Resolve to absolute, normalized path to prevent traversal attacks
        try:
            p = p.resolve()
        except (OSError, ValueError) as err:
            raise UserError(self.t("load_failed", err="invalid path")) from err
        # ALL users (including admins) must be within configured music_dirs
        # This prevents path traversal even when music_dirs is empty
        if not self.cfg.music_dirs:
            raise UserError(self.t("folders_admin"))
        music_dirs = [Path(d).resolve() for d in self.cfg.music_dirs if Path(d).is_dir()]
        if music_dirs and not any(p.is_relative_to(d) for d in music_dirs):
            raise UserError(self.t("folders_admin"))
        # Non-admin: must also be in the indexed music library
        if not admin and not self.index.contains(p):
            raise UserError(self.t("file_not_in_lib"))
        if p.is_dir():
            if not admin:
                raise UserError(self.t("folders_admin"))
            return scan_folder(p, limit=500, requester=user)
        if p.is_file() and p.suffix.lower() in MEDIA:
            return [local_track(p, user)]
        raise UserError(self.t("file_not_found"))

    def request(
        self,
        arg: str,
        user: str = "DJ",
        on_success: Callable[[list[Track]], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        """Admin request (GUI): no limits, runs in the background.

        Args:
            arg: The URL or search text to resolve.
            user: The user name for display in announcements.
            on_success: Optional callback called with (tracks) list on success.
            on_error: Optional callback called with (error_message) string on failure.
        """

        def job():
            req_id = self.start_request(arg, user)
            try:
                tracks = self.resolve(arg, user, True)
                if not tracks:
                    raise UserError(self.t("nothing_found"))
                pos = 0
                for t in tracks:
                    pos = self.queue.add_request(t)
                    self._log_track(t, "QUEUED", req_id)
                self.wake.set()
                if self.playlist:
                    self.playlist.add(tracks)
                if on_success:
                    on_success(tracks)
                else:
                    self.say(
                        self.t("queued_many", n=len(tracks), user=user)
                        if len(tracks) > 1
                        else self.t(
                            "queued_one",
                            pos=pos,
                            title=tracks[0].title,
                            dur=tracks[0].dur,
                            user=user,
                        )
                    )
                self.end_request(req_id, "completed")
            except UserError as ex:
                self.end_request(req_id, "failed")
                if on_error:
                    on_error(str(ex))
                else:
                    self.say(str(ex))
            except Exception:
                self.end_request(req_id, "failed")
                log.exception("request failed: %s", arg)
                if on_error:
                    on_error(self.t("error"))
                else:
                    self.say(self.t("error"))

        self.exec.submit(job)

    def load_source(self, src: str, limit: int = 0, max_dirs: int = 0) -> list[Track]:
        if is_url(src) or SEARCH_PREFIX.match(src):  # "ytsearch20:text" works as an autoplay source
            return self._remote(src, playlist=True, raw_target=True)
        p = Path(src)
        if p.is_dir():
            return scan_folder(p, limit=limit, max_dirs=max_dirs)
        if p.is_file():
            return [local_track(p)]
        raise UserError(self.t("not_found", src=src))

    def load_async(
        self,
        src: str,
        announce: bool = True,
        on_success: Callable[[list[Track]], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        limit: int = 0,
        max_dirs: int = 0,
    ) -> None:
        def job():
            try:
                tracks = self.load_source(src, limit=limit, max_dirs=max_dirs)
                self.queue.add_pool(tracks)
                self.wake.set()
                if self.playlist:
                    self.playlist.add(tracks)
                if on_success:
                    on_success(tracks)
                elif announce:
                    self.say(self.t("added_pool", n=len(tracks)))
            except Exception as ex:
                log.exception("load failed")
                if on_error:
                    on_error(str(ex))
                elif announce:
                    self.say(self.t("load_failed", err=ex))

        self.exec.submit(job)

    def _resolve_track_if_search(self, t: Track) -> Track:
        """Resolve a search-backed track (ytsearch1:...) to a real URL if needed.

        Raises UserError if resolution fails, so callers know not to play
        the unresolved search URL.
        """
        if not SEARCH_PREFIX.match(t.source):
            return t
        orig_src = t.source
        try:
            resolved = self._remote(
                orig_src,
                user=t.requester or "AutoDJ",
                playlist=False,
                search_limit=1,
                raw_target=True,
            )
            if resolved:
                res = resolved[0]
                res.state = "READY"
                if self.playlist:
                    self.playlist.update_source(orig_src, res)
                return res
            raise UserError(self.t("nothing_found"))
        except UserError:
            raise
        except Exception as ex:
            log.warning("failed to dynamically resolve search track %r: %s", orig_src, ex)
            raise UserError(str(ex)) from ex

    def _preload_search_tracks(self):
        """Asynchronously resolve upcoming search-backed tracks in the queue."""
        try:
            with self.queue.lock:
                candidates = [t for t in self.queue.requests if SEARCH_PREFIX.match(t.source)][:3]
            for cand in candidates:
                if self.stop_evt.is_set():
                    break
                resolved = self._resolve_track_if_search(cand)
                if resolved is not cand:
                    with self.queue.lock:
                        for idx, req in enumerate(self.queue.requests):
                            if req is cand or req.source == cand.source:
                                self.queue.requests[idx] = resolved
                                break
        except Exception:
            log.debug("preload search tracks encountered an issue", exc_info=True)

    def _load_all(self):
        self._load_library()
        self._load_autoplay_sources()
        self._load_playlist()
        self._load_playlist_dir()
        log.info(
            "autoplay pool: %d tracks; queue: %d requests",
            len(self.queue.pool),
            len(self.queue.requests),
        )
        self.wake.set()
        # Trigger background lookahead resolution for search tracks
        self.exec.submit(self._preload_search_tracks)

    def _load_library(self):
        try:
            self.index.scan()
            self.queue.add_pool(self.index.tracks)
        except Exception:
            log.exception("library scan failed")

    def _load_autoplay_sources(self):
        for s in self.cfg.autoplay_sources:
            try:
                self.queue.add_pool(self.load_source(s, limit=500))
            except Exception:
                log.exception("autoplay source failed: %s", s)

    def _load_playlist(self):
        # Add playlist tracks to the request queue so they are visible in the
        # GUI list box and play before the autoplay pool (requests first).
        # Dedupe against existing requests and recently played history so a
        # restart does not re-queue the same tracks.
        if not self.playlist:
            return
        try:
            loaded = self.playlist.load()
            with self.queue.lock:
                queued_sources = {r.source for r in self.queue.requests}
                played_sources = {t.source for t in self.history}
                for t in loaded:
                    if t.source not in queued_sources and t.source not in played_sources:
                        self.queue.add_request(t)
                        queued_sources.add(t.source)
        except Exception:
            log.exception("playlist load failed")

    def _load_playlist_dir(self):
        # Auto-load all *.json playlist files from playlist_dir (e.g. playlist/thai_pop.json)
        if not self.cfg.playlist_dir:
            return
        try:
            pl_dir = Path(self.cfg.playlist_dir)
            if not pl_dir.is_dir():
                return
            for pl_file in sorted(pl_dir.glob("*.json")):
                try:
                    dir_tracks = load_playlist(str(pl_file))
                    with self.queue.lock:
                        queued_sources = {r.source for r in self.queue.requests}
                        played_sources = {t.source for t in self.history}
                        for t in dir_tracks:
                            if t.source not in queued_sources and t.source not in played_sources:
                                self.queue.add_request(t)
                                queued_sources.add(t.source)
                    log.info(
                        "playlist dir: loaded %d track(s) from %s",
                        len(dir_tracks),
                        pl_file,
                    )
                except Exception:
                    log.exception("failed to load playlist dir file: %s", pl_file)
        except Exception:
            log.exception("playlist dir scan failed: %s", self.cfg.playlist_dir)

    # ---- playback loop --------------------------------------------------
    def _announce(self, t: Track):
        self.say(self.fmt_now(t))
        nxt = self.queue.peek()
        if self.cfg.announce_next and nxt:
            self.say(self.fmt_next(nxt))

    def _announce_if_playing(self, t: Track, wait: float = 3.0):
        """During a failure streak: announce only if the track is still playing after a few seconds."""
        if not self.stop_evt.wait(wait) and self.current is t:
            self._announce(t)

    def _check_autoplay_mode(self, now: float, idle_timeout: float) -> bool:
        """Check and update autoplay mode based on idle timeout.
        Returns True if autoplay mode should be used for next track."""
        has_requests = bool(self.queue.requests)
        if not has_requests and not self._autoplay_mode:
            if (
                self._last_user_request_time > 0
                and (now - self._last_user_request_time) >= idle_timeout
            ):
                if self.queue.pool:
                    self._autoplay_mode = True
                    log.info("Autoplay mode activated after %.0fs idle", idle_timeout)
                    self.say(self.t("autoplay_started"))
                else:
                    log.debug("No autoplay pool available, waiting for requests")

        # If in autoplay mode but new requests arrived, exit autoplay mode
        if self._autoplay_mode and has_requests:
            self._autoplay_mode = False
            log.info("Autoplay mode deactivated: new user request received")

        return self._autoplay_mode

    def _pop_next_track(self, is_request: bool) -> Track | None:
        """Pop the next track based on request/autoplay mode.

        Requests always take priority over the autoplay pool. When not in
        request mode, pick from the autoplay pool (shuffled or sequential).
        """
        if is_request and self.queue.requests:
            return self.queue.pop()
        if not is_request:
            return self.queue.pop_pool()
        return None

    def _player_loop(self):
        fails = 0  # consecutive tracks that failed to play
        idle_timeout = getattr(self.cfg, "autoplay_idle_timeout", 30.0)
        while not self.stop_evt.is_set():
            # Check circuit breaker before attempting playback
            if self._is_circuit_open():
                log.info("Circuit breaker open; waiting before next playback attempt")
                self.stop_evt.wait(10.0)
                continue

            # Check back-off: if we're in a back-off period, wait briefly and retry
            if self._backoff_until > 0 and time.monotonic() < self._backoff_until:
                self.stop_evt.wait(1.0)
                continue
            self._backoff_until = 0.0

            if not self._mpv_available():
                if fails == 0:
                    log.warning(
                        "mpv not available (mpv_path=%r); waiting for mpv before playing queue",
                        self.cfg.mpv_path,
                    )
                fails += 1
                self.stop_evt.wait(30.0)  # wait 30s before checking again
                continue

            now = time.monotonic()
            has_requests = bool(self.queue.requests)
            is_request = self._check_autoplay_mode(now, idle_timeout)
            is_request = has_requests or is_request  # prefer requests

            t = self._pop_next_track(is_request)
            if t is None:
                self.wake.wait(2)
                self.wake.clear()
                continue

            # Dynamic resolution for search-backed tracks (e.g. ytsearch1:... in playlist packs)
            try:
                t = self._resolve_track_if_search(t)
            except UserError as ex:
                log.warning("failed to resolve track %r: %s", t.source, ex)
                fails += 1
                self._track_failed(t, fails)
                self._record_circuit_failure()
                continue

            # After popping and resolving current, trigger preload for next in queue
            self.exec.submit(self._preload_search_tracks)
            fails = self._play_one_track(t, fails, is_request=is_request)

    def _mpv_available(self) -> bool:
        # Players without an `available` method (e.g. test fakes) are treated as available.
        if not hasattr(self.player, "available"):
            return True
        return bool(self.player.available())

    def _announce_playback_failure(self, t: Track, fails: int) -> None:
        if fails <= MAX_FAIL_ANNOUNCE:
            self.say(self.t("cannot_play", title=t.title))
        elif fails == MAX_FAIL_ANNOUNCE + 1:
            log.warning(
                "%d tracks in a row failed to play: not announcing further failures in the room "
                "(check the lines above; run AutoDJ.exe --check)",
                fails - 1,
            )

    def _track_failed(self, t: Track, fails: int) -> None:
        """Mark *t* failed, announce per the back-off policy, then back off.

        The back-off is non-blocking: we record the failure time and let the
        player loop check it on the next iteration instead of blocking the
        thread with stop_evt.wait().
        """
        t.state = "FAILED"
        self._log_track(t, "FAILED")
        self.current = None
        self._announce_playback_failure(t, fails)
        # Record back-off time; the player loop checks _backoff_until before playing
        self._backoff_until = time.monotonic() + self.fail_delay(fails)

    def _try_play(self, t: Track) -> bool:
        try:
            return self.player.play(t.source, self.volume, t.duration)
        except Exception:
            log.exception(
                "cannot start mpv (mpv_path=%r): install mpv and set mpv_path in config.toml",
                self.cfg.mpv_path,
            )
            return False

    def _play_one_track(self, t: Track, fails: int, is_request: bool = False) -> int:
        """Play *t* (retrying pool tracks on failure with exponential backoff,
        but advancing immediately for user requests) until it completes or the loop stops.

        Returns the updated consecutive-failure count.
        """
        recorded = False
        max_retries = MAX_FAIL_ANNOUNCE if not is_request else 0  # retry pool tracks, not requests
        while not self.stop_evt.is_set():
            self.current = t
            t.state = "PLAYING"
            self._log_track(t, "PLAYING")
            self.votes.clear()
            self.paused, self._paused_at, self._paused_total = False, None, 0.0
            self.started_at = time.monotonic()
            if fails < MAX_FAIL_ANNOUNCE:
                self._announce(t)
            else:
                self.exec.submit(self._announce_if_playing, t)
            log.info("playing %s", t.source)
            # Emit track_start event for plugins
            if self._plugin_manager:
                self._plugin_manager.emit("track_start", t)
            if not self._try_play(t):
                fails += 1
                self._track_failed(t, fails)
                self._record_circuit_failure()
                # Emit track_failed event for plugins
                if self._plugin_manager:
                    self._plugin_manager.emit(
                        "track_failed", {"track": t, "error": "playback failed"}
                    )
                # Retry the same track if we haven't exceeded max retries (pool tracks only)
                if fails < max_retries:
                    log.info(
                        "retrying track %r (attempt %d/%d)",
                        t.source,
                        fails + 1,
                        max_retries,
                    )
                    continue
                # Max retries exceeded (or zero retries for requests), give up and move to next track
                return fails
            fails = 0
            self._record_circuit_success()
            if not recorded:
                t.state = "COMPLETED"
                self._log_track(t, "COMPLETED")
                self.history.appendleft(t)
                recorded = True
                # Emit track_end event for plugins
                if self._plugin_manager:
                    self._plugin_manager.emit("track_end", t)
            if self.queue.repeat != "one" or getattr(self.player, "skipped", False):
                break
        self.current = None
        return fails

    # ---- main -----------------------------------------------------------
    def _chat_loop(self):
        try:
            for msg in self.adapter.messages():
                if self.stop_evt.is_set():
                    break
                if self._should_ignore_message(msg):
                    continue

                if msg.is_im:
                    self._handle_im(msg)
                else:
                    self._handle_room_message(msg)
        except (OSError, RuntimeError, ChatAdapterError):
            # Expected adapter-level failures at shutdown or COM wedges
            if not self.stop_evt.is_set():
                log.exception("chat loop ended with adapter error")
        except Exception:
            # Unexpected: log but don't crash the bot
            if not self.stop_evt.is_set():
                log.exception("chat loop ended with unexpected error")
        finally:
            self.chat_done.set()

    def _should_ignore_message(self, msg: ChatMessage) -> bool:
        """Return True if the message should be ignored (echo or own message)."""
        return norm(msg.user).lower() == self.cfg.bot_nick.lower() or self._is_echo(msg.text)

    def _handle_im(self, msg: ChatMessage) -> None:
        """Handle an instant/private message."""
        self.log_chat(msg.user, msg.text)
        self._log_im_message(msg)
        if self.cfg.im_auto_reply_enabled:
            self._handle_im_message(msg)

    def _handle_room_message(self, msg: ChatMessage) -> None:
        """Handle a room message (non-IM)."""
        # Per-nick chat rate limiting (non-admins only)
        if msg.user.lower() not in self.admins:
            if not self._check_chat_rate_limit(msg.user):
                log.info("Chat rate limit: dropping message from %s", msg.user)
                return

        self.log_chat(msg.user, msg.text)

        # Track active room users
        self._update_participant_count(msg.user)
        # Camfrog RE integrations: gift announcement + upgrade/payment status alert
        self._handle_re_events(msg)

        self._handle_admin_greeting(msg)
        self._handle_welcome_message(msg)

        # Update last user request time for !play commands (tracked in router)
        self.exec.submit(self.router.handle, msg)

    @property
    def participant_count(self) -> int:
        """Estimated number of participants in the room (from chat activity)."""
        return self._participant_count

    def _update_participant_count(self, user: str):
        """Update participant tracking from chat activity."""
        self._active_room_users.add(user.lower())
        self._participant_count = len(self._active_room_users)

    def _log_im_message(self, msg: ChatMessage) -> None:
        """Log an IM / private message for the IM viewer GUI (read-only)."""
        self.im_log.append((msg.user, msg.text))
        self.im_seq += 1

    def _handle_admin_greeting(self, msg: ChatMessage) -> None:
        """Greet an admin on their first message of the session (if enabled)."""
        if not self.cfg.admin_greeting_enabled:
            return
        if msg.user.lower() not in self.admins:
            return
        now = time.monotonic()
        last_greeting = self._admin_greeting_cooldowns.get(msg.user.lower(), 0.0)
        if now - last_greeting < self.cfg.admin_greeting_cooldown:
            return
        greeting = self.cfg.admin_greeting_message.format(admin=msg.user)
        self.say(greeting)
        self._admin_greeting_cooldowns[msg.user.lower()] = now
        log.info("Sent admin greeting to %s", msg.user)

    # ---- Camfrog reverse-engineering integrations -------------------------

    _GIFT_KEYWORDS = (
        "gift_received",
        "room_gift_message",
        "camfrog://gift",
        "camfrog://vgift",
        "send_vgift",
        "virtual_gift",
        "vgift_",
        "you_give_virtual_gift_report",
        "give_virtual_gift_report",
        "top_gifter",
        "recent_gifter",
        "gift_store",
    )
    _STATUS_KEYWORDS = (
        "upgrade required",
        "payment required",
        "payment gateway capabilities",
    )
    # Avatar change keywords (Camfrog avatar system; see docs/camfrog-re/16-user-icon-avatar.md)
    _AVATAR_KEYWORDS = (
        "updateavatarmessage",
        "avatar_changed",
        "avatarchange",
        "changavatar",
    )
    # Status indicator keywords -> message key (Camfrog status PNGs; see docs/camfrog-re/14-png-assets.md)
    _STATUS_INDICATOR_KEYWORDS: dict[str, str] = {
        "online": "status_online",
        "away": "status_away",
        "busy": "status_busy",
        "invisible": "status_invisible",
        "admin": "status_admin",
        "moderator": "status_moderator",
        "owner": "status_owner",
    }
    # Name color regex: style='color: #RRGGBB' or style="color: #RRGGBB" (Camfrog nickname color; see docs/camfrog-re/15-name-color.md)
    _NICK_COLOR_RE = re.compile(r"color:\s*#([0-9a-fA-F]{6})")

    def _handle_re_events(self, msg: ChatMessage) -> None:
        """Handle Camfrog reverse-engineering events from a room chat message.

        Detects virtual-gift messages (announce them), avatar changes (announce them),
        user status indicators (online/away/busy/invisible/admin/moderator/owner), and
        upgrade/payment-required status text (alert the admin). See docs/camfrog-re/.
        """
        body = self._chat_body(msg.text)
        if not body:
            return
        nick = msg.user
        if self.cfg.gift_announce_enabled and self._is_gift_message(body):
            self._announce_gift(nick, body)
        if self.cfg.avatar_change_enabled and self._is_avatar_change(body):
            self._announce_avatar_change(nick)
        if self.cfg.status_indicator_enabled:
            self._announce_status_indicator(nick, body)
        if self.cfg.status_alert_enabled and self._is_status_message(body):
            self._alert_status(nick, body)
        # Track name colors from incoming chat HTML for GUI preview (read-only; see docs/camfrog-re/15-name-color.md)
        self._track_name_color(nick, body)

    def _chat_body(self, text: str) -> str:
        """Extract the message body from a 'TIME nick: BODY' chat line."""
        m = re.match(
            r"^(?:\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?\s+)?(?P<nick>[^:]{1,30}):\s*(?P<rest>.*)$",
            text,
            re.IGNORECASE,
        )
        if m:
            return m.group("rest")
        _, sep, rest = text.partition(": ")
        return rest if sep else text

    def _is_gift_message(self, body: str) -> bool:
        low = body.lower()
        return any(k in low for k in self._GIFT_KEYWORDS)

    def _is_avatar_change(self, body: str) -> bool:
        low = body.lower()
        return any(k in low for k in self._AVATAR_KEYWORDS)

    def _is_status_message(self, body: str) -> bool:
        low = body.lower()
        return any(k in low for k in self._STATUS_KEYWORDS)

    def _is_status_indicator(self, body: str) -> str | None:
        """Return the message key for a status indicator keyword found in body, else None."""
        low = body.lower()
        for keyword, msg_key in self._STATUS_INDICATOR_KEYWORDS.items():
            if keyword in low:
                return msg_key
        return None

    def _announce_gift(self, nick: str, body: str) -> None:
        """Announce a virtual gift detected in room chat."""
        try:
            text = self.t("gift_announce", nick=nick)
        except Exception:
            text = f"{nick} sent a virtual gift! 🎁"
        self.say(text)
        log.info("gift announced from %s: %r", nick, body[:120])

    def _announce_avatar_change(self, nick: str) -> None:
        """Announce an avatar change detected in room chat."""
        try:
            text = self.t("avatar_change_announce", nick=nick)
        except Exception:
            text = f"{nick} changed their avatar! 🖼️"
        self.say(text)
        log.info("avatar change announced from %s", nick)

    def _announce_status_indicator(self, nick: str, body: str) -> None:
        """Announce a user status indicator detected in room chat."""
        msg_key = self._is_status_indicator(body)
        if not msg_key:
            return
        try:
            text = self.t(msg_key, nick=nick)
        except Exception:
            text = f"{nick} status update: {msg_key}"
        self.say(text)
        log.info("status indicator announced from %s: %s", nick, msg_key)

    def _alert_status(self, nick: str, body: str) -> None:
        """Alert when Camfrog shows upgrade/payment-required status text."""
        log.warning("Camfrog status from %s: %r", nick, body[:160])
        low = body.lower()
        text = (
            self.t("status_payment_required")
            if "payment" in low
            else self.t("status_upgrade_required")
        )
        try:
            self.say(text)
        except Exception:
            log.exception("failed to announce status alert")

    def _track_name_color(self, nick: str, body: str) -> None:
        """Extract nickname color from incoming chat HTML for GUI preview.

        Camfrog renders usernames with inline style='color: #RRGGBB'. AutoDJ cannot
        set name color (client-controlled, outgoing messages are plain text), but it
        can read/display the colors from incoming messages for its local GUI preview,
        mirroring Camfrog's default palette. See docs/camfrog-re/15-name-color.md.
        """
        m = self._NICK_COLOR_RE.search(body)
        if not m:
            return
        color = f"#{m.group(1)}"
        self._name_colors[nick.lower()] = color
        log.debug("tracked name color for %s: %s", nick, color)

    def _handle_welcome_message(self, msg):
        """Send welcome message to a user on their first message in a session.

        Only for non-IM messages. Rate-limited per user using welcome_message_cooldown
        to avoid spam. Thread-safe per-user cooldown tracking.
        """
        if not self.cfg.welcome_message_enabled or msg.is_im:
            return
        now = time.monotonic()
        key = f"welcome:{msg.user.lower()}"
        cooldown = getattr(self.cfg, "welcome_message_cooldown", 3600.0)
        should_send = False
        welcome_text = ""
        with self._chat_lock:
            last_welcome = self._welcome_cooldowns.get(key, 0.0)
            if now - last_welcome >= cooldown:
                welcome_text = self.cfg.welcome_message_message
                # Replace {room} placeholder if present
                if "{room}" in welcome_text:
                    welcome_text = welcome_text.replace("{room}", self.cfg.room)
                should_send = True
                self._welcome_cooldowns[key] = now
        if should_send:
            self.say(welcome_text)
            log.info("Sent welcome message to %s", msg.user)

    def start(self):
        """Non-blocking: used by the GUI."""
        if hasattr(self.player, "available") and not self.player.available():
            log.error(
                'mpv not found (mpv_path=%r). Install mpv and set mpv_path = "C:/mpv/mpv.exe" '
                "in config.toml; nothing will play until then.",
                self.cfg.mpv_path,
            )
        # Load plugins
        if self._plugin_manager:
            self._plugin_manager.load_plugins()
        # Start webhook server if enabled
        if self._webhook_server:
            import asyncio

            webhook_server = self._webhook_server

            def run_webhook():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(webhook_server.start())

            t = threading.Thread(target=run_webhook, daemon=True, name="autodj-webhook")
            self._threads.append(t)
            t.start()

        for fn in (
            self._sender,
            self._player_loop,
            self._load_all,
            self._chat_loop,
            self._auto_reply_loop,
            self._im_auto_reply_loop,
            self._rate_limit_cleanup_loop,
        ):
            t = threading.Thread(target=fn, daemon=True, name=f"autodj-{fn.__name__}")
            self._threads.append(t)
            t.start()

    def _auto_reply_loop(self):
        """Send scheduled auto-reply messages from ads-list.json to the room.

        Messages are selected randomly from ads-list.json and sent every
        auto_reply_interval seconds (minimum 60s). The loop rotates through
        all messages before repeating any, ensuring fair distribution.
        """
        if not self.cfg.auto_reply_enabled:
            log.debug("auto-reply disabled; loop not started")
            return
        path = self.cfg.auto_reply_file
        # Resolve relative paths against the config file directory so the file
        # is found regardless of the current working directory.
        if not os.path.isabs(path) and self.cfg_path:
            path = str(Path(self.cfg_path).parent / path)
        messages = self._load_auto_reply_messages(path)
        if not messages:
            log.warning("auto-reply enabled but no messages found in %r", path)
            return
        interval = max(60.0, self.cfg.auto_reply_interval)  # minimum 60s to avoid spam
        # Shuffled rotation: cycle through all messages randomly, reshuffle after each full cycle
        shuffled = list(messages)
        random.shuffle(shuffled)
        idx = 0
        while not self.stop_evt.is_set():
            # Wait between messages, but wake up immediately on shutdown
            if self.stop_evt.wait(interval):
                break
            if self.stop_evt.is_set():
                break
            msg = shuffled[idx]
            idx += 1
            # Reshuffle when we've gone through all messages
            if idx >= len(shuffled):
                random.shuffle(shuffled)
                idx = 0
            try:
                self.say(msg)
                log.info("auto-reply sent: %r", msg[:60])
            except Exception:
                log.exception("auto-reply send failed")

    @staticmethod
    def _extract_entries_from_data(data, path: str):
        """Extract entries list from various JSON formats."""
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            for key in ("messages", "ads", "entries", "items"):
                if key in data and isinstance(data[key], list):
                    return data[key]
            log.warning(
                "auto-reply file %r: no valid messages list found (tried keys: messages, ads, entries, items)",
                path,
            )
            return []
        else:
            log.warning("auto-reply file %r: root must be a list or dict", path)
            return []

    @staticmethod
    def _sanitize_messages(entries):
        """Filter and sanitize message entries."""
        messages = []
        for m in entries:
            if m is None:
                continue
            s = str(m).strip()
            if s:
                messages.append(s)
        return messages

    @staticmethod
    def _load_auto_reply_messages(path: str) -> list[str]:
        """Load messages from ads-list.json. Returns a list of message strings.

        Supports formats:
        - {"messages": ["msg1", "msg2"]}
        - {"version": 1, "messages": ["msg1", "msg2"]}
        - ["msg1", "msg2"]
        - {"ads": ["msg1", "msg2"]} (legacy)
        """
        try:
            data = json.loads(Path(path).read_text("utf-8-sig"))
        except FileNotFoundError:
            log.debug("auto-reply file %r not found", path)
            return []
        except json.JSONDecodeError as ex:
            log.warning("auto-reply file %r has invalid JSON: %s", path, ex)
            return []
        except Exception:
            log.warning("cannot read auto-reply file %r", path, exc_info=True)
            return []

        entries = Engine._extract_entries_from_data(data, path)
        messages = Engine._sanitize_messages(entries)

        if not messages:
            log.warning("auto-reply file %r: no valid messages after filtering", path)

        return messages

    def _im_auto_reply_loop(self):
        """Background cleanup for IM reply cooldowns.

        The actual IM auto-reply is handled in _handle_im_message (called from chat loop).
        This loop just periodically cleans up stale cooldown entries to prevent memory growth.
        """
        if not self.cfg.im_auto_reply_enabled:
            log.debug("IM auto-reply disabled; loop not started")
            return
        log.info("IM auto-reply cooldown cleanup enabled")
        while not self.stop_evt.is_set():
            if self.stop_evt.wait(60.0):  # cleanup every 60 seconds
                break
            now = time.monotonic()
            cutoff = now - self.cfg.im_auto_reply_cooldown * 2  # keep 2x cooldown window
            with self._chat_lock:  # reuse existing lock for thread safety
                stale = [u for u, t in self._im_reply_cooldowns.items() if t < cutoff]
                for u in stale:
                    del self._im_reply_cooldowns[u]
                if stale:
                    log.debug("Cleaned up %d stale IM reply cooldowns", len(stale))

    def _handle_im_message(self, msg: ChatMessage):
        """Handle incoming IM (private message) and send auto-reply if enabled."""
        if not self.cfg.im_auto_reply_enabled:
            return
        if not msg.is_im:
            return
        user = msg.user.lower()
        now = time.monotonic()
        with self._chat_lock:  # protect _im_reply_cooldowns across chat loop and cleanup loop
            last_reply = self._im_reply_cooldowns.get(user, 0.0)
            if now - last_reply < self.cfg.im_auto_reply_cooldown:
                log.debug("IM auto-reply on cooldown for %s", user)
                return
            # Send auto-reply
            reply_text = self.cfg.im_auto_reply_message
            if reply_text:
                try:
                    self.say(f"[IM] {reply_text}")
                    self._im_reply_cooldowns[user] = time.monotonic()
                    log.info("Sent IM auto-reply to %s", msg.user)
                except Exception:
                    log.exception("Failed to send IM auto-reply to %s", msg.user)

    def _rate_limit_cleanup_loop(self):
        """Periodically clean up expired rate limit entries in the Router.

        Runs every 60 seconds to prevent memory growth from stale entries.
        """
        while not self.stop_evt.is_set():
            if self.stop_evt.wait(60.0):
                break
            if self.stop_evt.is_set():
                break
            try:
                import time

                now = time.monotonic()
                self.router.cleanup_expired_entries(now)
            except Exception:
                log.exception("Rate limit cleanup failed")

    def run(self):
        self.start()
        try:
            while not self.chat_done.wait(0.5):
                pass
            end = time.monotonic() + 3  # let queued replies flush
            while not self.outbox.empty() and time.monotonic() < end:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    # ---- Circuit breaker -------------------------------------------------------

    def _record_circuit_failure(self) -> None:
        """Record a playback failure and open the circuit breaker if threshold exceeded."""
        with self._circuit_breaker_lock:
            self._circuit_breaker_failures += 1
            if self._circuit_breaker_failures >= _CIRCUIT_BREAKER_FAILURE_THRESHOLD:
                self._circuit_breaker_open_until = time.monotonic() + _CIRCUIT_BREAKER_RESET_TIMEOUT
                log.warning(
                    "Circuit breaker OPEN: %d consecutive failures; pausing playback for %.0fs",
                    self._circuit_breaker_failures,
                    _CIRCUIT_BREAKER_RESET_TIMEOUT,
                )

    def _record_circuit_success(self) -> None:
        """Record a successful playback and reset the circuit breaker."""
        with self._circuit_breaker_lock:
            if self._circuit_breaker_failures > 0:
                log.info(
                    "Circuit breaker CLOSED after %d failures; playback recovered",
                    self._circuit_breaker_failures,
                )
            self._circuit_breaker_failures = 0
            self._circuit_breaker_open_until = 0.0

    def _is_circuit_open(self) -> bool:
        """Return True if the circuit breaker is open (playback paused due to failures)."""
        with self._circuit_breaker_lock:
            if self._circuit_breaker_open_until <= 0.0:
                return False
            if time.monotonic() >= self._circuit_breaker_open_until:
                # Half-open: allow one attempt
                self._circuit_breaker_open_until = 0.0
                self._circuit_breaker_failures = 0
                log.info("Circuit breaker HALF-OPEN: allowing one playback attempt")
                return False
            return True

    def _record_send_failure(self) -> None:
        """Record a chat send failure and track consecutive count."""
        with self._send_failure_lock:
            self._send_failure_count += 1
            count = self._send_failure_count
        if count >= _MAX_CONSECUTIVE_SEND_FAILURES:
            log.error(
                "Chat send circuit breaker: %d consecutive send failures; suspending sends",
                count,
            )

    def _record_send_success(self) -> None:
        """Record a successful chat send and reset failure count."""
        with self._send_failure_lock:
            if self._send_failure_count > 0:
                log.info("Chat send recovered after %d failures", self._send_failure_count)
            self._send_failure_count = 0

    def _is_send_suspended(self) -> bool:
        """Return True if chat sends are suspended due to repeated failures."""
        with self._send_failure_lock:
            return self._send_failure_count >= _MAX_CONSECUTIVE_SEND_FAILURES

    # ---- Per-nick chat rate limiting -----------------------------------------

    def _check_chat_rate_limit(self, nick: str) -> bool:
        """Return True if *nick* is allowed to send a chat message now.

        Uses a sliding window: at most _CHAT_RATE_LIMIT_MAX messages per
        _CHAT_RATE_LIMIT_WINDOW seconds per nick.
        Optimized with deque for O(1) popleft operations.
        """
        now = time.monotonic()
        with self._chat_rate_lock:
            window = self._chat_rate_window.setdefault(nick, deque())
            # Prune expired entries efficiently with popleft
            cutoff = now - _CHAT_RATE_LIMIT_WINDOW
            while window and window[0] <= cutoff:
                window.popleft()
            if len(window) >= _CHAT_RATE_LIMIT_MAX:
                log.warning("Chat rate limit exceeded for nick=%s", nick)
                return False
            window.append(now)
            return True

    # ---- Health check ----------------------------------------------------------

    def health_check(self) -> dict[str, object]:
        """Return a structured health status dict for monitoring dashboards.

        Never raises — every check is wrapped in try/except so a single
        failing subsystem cannot break the whole report.
        """
        checks: dict[str, dict[str, object]] = {}
        ok = True

        # mpv availability
        try:
            mpv_ok = bool(self._mpv_available())
            checks["mpv"] = {
                "ok": mpv_ok,
                "details": "available" if mpv_ok else "not available",
            }
            if not mpv_ok:
                ok = False
        except Exception as ex:  # noqa: BLE001 - health check must not crash
            checks["mpv"] = {"ok": False, "details": str(ex)}
            ok = False

        # Circuit breaker state (read under circuit breaker lock for consistent snapshot)
        with self._circuit_breaker_lock:
            cb_open = self._is_circuit_open()
            cb_failures = self._circuit_breaker_failures
            cb_open_until = self._circuit_breaker_open_until
        checks["circuit_breaker"] = {
            "ok": not cb_open,
            "failures": cb_failures,
            "open_until": cb_open_until,
        }
        if cb_open:
            ok = False

        # Send suspension state
        with self._send_failure_lock:
            send_suspended = self._is_send_suspended()
            send_failures = self._send_failure_count
        checks["chat_send"] = {
            "ok": not send_suspended,
            "failures": send_failures,
        }
        if send_suspended:
            ok = False

        # Queue state
        try:
            with self.queue.lock:
                q_len = len(self.queue.requests)
                p_len = len(self.queue.pool)
            checks["queue"] = {
                "ok": True,
                "requests": q_len,
                "pool": p_len,
            }
        except Exception as ex:  # noqa: BLE001
            checks["queue"] = {"ok": False, "details": str(ex)}
            ok = False

        # IM log state
        try:
            im_seq, im_entries = self.im_snapshot()
            checks["im_viewer"] = {
                "ok": True,
                "seq": im_seq,
                "entries": len(im_entries),
            }
        except Exception as ex:  # noqa: BLE001
            checks["im_viewer"] = {"ok": False, "details": str(ex)}
            ok = False

        return {"ok": ok, "checks": checks, "timestamp": time.monotonic()}

    # ---- admin: mic mute / unmute ----------------------------------------

    def mute_mic(self, muted: bool):
        """Mute or unmute the mic output via player volume.

        Sets player volume to 0 when muted, restores previous volume when unmuted.
        This affects AutoDJ's music output, not the Camfrog mic device directly.
        """
        if muted:
            self._mic_prev_volume = self.volume
            self.set_volume(0)
            self.mute_enabled = True
            log.info("Mic muted by admin")
        else:
            self.set_volume(getattr(self, "_mic_prev_volume", 70))
            self.mute_enabled = False
            log.info("Mic unmuted by admin")

    # ---- admin: kick / ban / unban / punish ------------------------------

    def kick_user(self, nick: str):
        """Kick a user from the room via Camfrog /kick command."""
        self.say(f"/kick {nick}")
        log.info("Kicked user: %s", nick)

    def ban_user(self, nick: str):
        """Ban a user from the room via Camfrog /ban command."""
        self.say(f"/ban {nick}")
        log.info("Banned user: %s", nick)

    def unban_user(self, nick: str):
        """Unban a user from the room via Camfrog /unban command."""
        self.say(f"/unban {nick}")
        log.info("Unbanned user: %s", nick)

    def punish_user(self, nick: str):
        """Punish a user via Camfrog /punish command."""
        self.say(f"/punish {nick}")
        log.info("Punished user: %s", nick)

    def punish_bot(self, nick: str):
        """Punish a bot via Camfrog /punish command."""
        self.say(f"/punish {nick}")
        log.info("Punished bot: %s", nick)

    # ---- admin: delete message -------------------------------------------

    def delete_message(self, msg_id: str) -> bool:
        """Delete a message by its ID via Camfrog /delete command.

        Returns True if the delete command was sent, False if disabled.
        """
        if not getattr(self.cfg, "admin_delete_message_enabled", False):
            return False
        self.say(f"/delete {msg_id}")
        log.info("Deleted message id: %s", msg_id)
        return True

    # ---- admin: welcome message ------------------------------------------

    def set_welcome_message(self, text: str):
        """Set the welcome message shown when a user first joins the room."""
        self.cfg.welcome_message_message = text
        self.cfg.welcome_message_enabled = True
        log.info("Welcome message set: %r", text)

    def shutdown(self):
        self.stop_evt.set()
        self.wake.set()
        self.player.stop()
        # Unload plugins
        if self._plugin_manager:
            self._plugin_manager.unload_plugins()
        # Stop webhook server
        if self._webhook_server:
            import asyncio

            webhook_server = self._webhook_server

            def stop_webhook():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(webhook_server.stop())

            stop_webhook()
        self.adapter.close()
        self.exec.shutdown(wait=False, cancel_futures=True)
        # Shutdown TTS worker
        from .tts import shutdown_tts

        shutdown_tts()
        # Shutdown library caches
        from .library import shutdown_library_caches

        shutdown_library_caches()
        # Join daemon threads with a timeout so shutdown does not hang forever.
        for t in self._threads:
            if t.is_alive():
                t.join(timeout=5.0)
