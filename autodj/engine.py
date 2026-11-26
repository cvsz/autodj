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
from .ai import AIClient
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
from .models import Track, fmt_time
from .player import MpvPlayer
from .playlist import PlaylistStore, load_playlist
from .playqueue import PlayQueue
from .textutil import clean_text, norm
from .updater import Updater

log = logging.getLogger("autodj")

MAX_FAIL_ANNOUNCE = (
    3  # consecutive failed tracks announced in the room; after that only the log hears about it
)
MAX_BACKOFF = 30.0  # seconds, ceiling of the pause between consecutive failed tracks
RECENT_FAIL_TTL = 600.0  # seconds a failed song is skipped before it may be retried
AI_MAX_INFLIGHT = 2  # concurrent AI provider calls; further `!ai ask` get a 'busy' reply
ECHO_TTL = 120.0  # seconds a line we posted is remembered, to recognise it when it comes back from the room

# Failure categories for structured diagnostics
FAIL_RESOLVE = "resolve_failed"  # yt-dlp/search could not resolve the source
FAIL_PLAYBACK = "playback_failed"  # mpv could not play the track
FAIL_HUNG = "playback_hung"  # mpv did not exit within the expected time
FAIL_CRASH = "playback_crashed"  # mpv exited with non-zero code
FAIL_DELIVERY = "chat_delivery_failed"  # chat message could not be delivered
FAIL_DROPPED = "chat_dropped"  # no chat connection (NullAdapter): message discarded
MAX_DELIVERY_RECORDS = 500  # delivery log kept in memory (the bot runs 24/7)
FAIL_CONFIG = "config_error"  # configuration problem

_req_ids = itertools.count()  # global request ID_counter

# Circuit breaker thresholds
_CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5  # consecutive failures before opening
_CIRCUIT_BREAKER_RESET_TIMEOUT = 60.0  # seconds before attempting half-open
_MAX_CONSECUTIVE_SEND_FAILURES = 10  # stop retrying chat sends after this many failures

# Per-nick chat rate limiting (prevents spam flooding)
_CHAT_RATE_LIMIT_WINDOW = 60.0  # seconds
_CHAT_RATE_LIMIT_MAX = 20  # max messages per nick per window


def _fill(template: str, **values: str) -> str:
    """Replace ``{name}`` placeholders without ``str.format`` (a stray brace or an
    unknown placeholder in a user-edited message must never raise)."""
    for k, v in values.items():
        template = template.replace("{" + k + "}", v)
    return template


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
        self._active_room_users: set[str] = set()
        self._participant_count = 0
        self._autoplay_mode = False
        self._voteskip_cooldown_lock = threading.Lock()
        self._voteskip_cooldowns: dict[str, float] = {}
        self._last_user_request_time = 0.0
        self.outbox: queue.Queue[str] = queue.Queue()
        self.chat_log: deque[tuple[str, str]] = deque(maxlen=300)
        self.chat_seq = 0
        self._chat_version = (
            0  # bumped on every chat_log mutation; GUI can skip refresh when unchanged
        )
        self.im_seq = 0  # IM message sequence counter; GUI polls im_snapshot()
        self._im_version = 0  # bumped on every im_log mutation; GUI can skip refresh when unchanged
        self.im_log: list[tuple[str, str]] = []  # IM chat log
        self.chat_done = threading.Event()
        self.wake = threading.Event()
        self.exec = ThreadPoolExecutor(
            8
        )  # lookups can take seconds: keep !skip and friends responsive meanwhile
        # Delayed welcomes use independent daemon timers: sleeping on the shared
        # worker pool would starve commands when many users join at once.
        self._welcome_timers: set[threading.Timer] = set()
        self._welcome_timers_lock = threading.Lock()
        # AI calls wait on a remote provider (up to its timeout): give them their own
        # small pool so a slow provider can never starve command handling in self.exec.
        self._ai_exec = ThreadPoolExecutor(AI_MAX_INFLIGHT, thread_name_prefix="autodj-ai")
        self._ai_inflight = 0
        self._ai_inflight_lock = threading.Lock()
        self.history: deque[Track] = deque(maxlen=20)  # newest first
        # Tracks that just failed: key -> monotonic expiry. Time-bounded so a
        # failed request becomes playable again later (a count-bounded deque
        # never forgot anything and could stall the player for good).
        self._recent_failed: dict[str, float] = {}
        self._recent_failed_lock = threading.Lock()
        self._stats_lock = threading.Lock()  # serialises top_requests.json read-modify-write
        self.blocked: set[str] = {b.lower() for b in cfg.blocked_users}
        self.fail_delay = lambda n: min(
            MAX_BACKOFF, 2.0 ** (n - 1)
        )  # n = consecutive failures so far
        self._backoff_until = 0.0  # monotonic time until playback may resume after failures
        self._sent: deque[tuple[float, str]] = deque(maxlen=64)
        # Camfrog shows our own posts under the account's nick (e.g. Seaza), which
        # differs from bot_nick; learned from echoes so the bot never greets itself.
        self._own_nicks: set[str] = set()
        self._sent_lock = threading.Lock()
        self._chat_lock = threading.Lock()  # guards chat_log + chat_seq (GUI polls them)
        self._chat_rate_lock = threading.Lock()  # guards _chat_rate_limit state
        self._chat_rate_window: dict[
            str, deque
        ] = {}  # nick -> deque of timestamps for rate limiting
        # Recently processed (user, text) pairs to drop duplicate deliveries from
        # the chat adapter (Camfrog can re-dump a backlog of identical lines).
        self._recent_messages: dict[str, float] = {}
        self._recent_messages_lock = threading.Lock()
        self._plugin_manager = None  # built from cfg.plugins below; loaded in start()
        if getattr(cfg, "plugins", None):
            from .plugins.manager import PluginManager

            self._plugin_manager = PluginManager(self, list(cfg.plugins))
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
        # ---- Camfrog RE / greeting / welcome cooldowns ------------------------
        self._admin_greeting_cooldowns: dict[str, float] = {}
        self._welcome_cooldowns: dict[str, float] = {}
        self._mic_greeting_cooldowns: dict[str, float] = {}
        self._name_colors: dict[str, str] = {}
        self._im_reply_cooldowns: dict[str, float] = {}
        # ---- Circuit breaker --------------------------------------------------
        self._circuit_breaker_lock = threading.Lock()
        self._circuit_breaker_failures = 0
        self._circuit_breaker_open_until = 0.0
        # ---- Chat send failure tracking ---------------------------------------
        self._send_failure_lock = threading.Lock()
        self._send_failure_count = 0
        # ---- Optional subsystems ----------------------------------------------
        self._config_watcher = None  # set up by the GUI if hot reload is enabled
        self._webhook_server = None  # set up by the GUI if webhook is enabled
        self.updater = Updater(self.cfg, engine=self)  # auto-update checker/downloader
        self.ai = AIClient(self.cfg)  # AI chat client (disabled by default)
        self._np_question_last = float("-inf")  # last "what song?" auto-answer (monotonic)
        # Default song (config ``default_track``): plays at startup and again
        # whenever the request queue is empty and nobody has requested anything
        # for ``autoplay_idle_timeout`` seconds.  It is never a request, so a new
        # request cuts it immediately (see preempt_unrequested).
        self._default_meta: Track | None = None  # cached title/duration lookup
        self._default_failed_until = 0.0  # after a failed play, use the pool for a while
        self._default_lookup_retry_at = 0.0  # after a failed metadata lookup
        # When the player first found the request queue empty (monotonic), i.e.
        # when the last requested song finished.  The idle timeout counts from
        # here, so a long request is still followed by a full idle window.
        self._queue_empty_since: float | None = None

    # ---- text -----------------------------------------------------------
    def t(self, key: str, **kw) -> str:
        return tr(self.lang, key, **kw)

    def _time_fields(self, t: Track) -> dict:
        """Template fields beyond Track.fields(): progress of the current song and
        when the next one starts.  Usable in msg_now / msg_next as
        {elapsed} {remaining} {eta}; unknown values render as "?"."""
        cur = self.current
        elapsed = remaining = None
        if cur is not None:
            try:
                elapsed = self.position()
            except Exception:  # IPC hiccup must never break an announcement
                elapsed = None
            if elapsed is not None:
                elapsed = float(round(elapsed))  # whole seconds, so totals add up in chat
            if cur.duration and elapsed is not None:
                elapsed = min(elapsed, cur.duration)
                remaining = max(0.0, cur.duration - elapsed)
        if t is cur:
            return {
                "elapsed": fmt_time(elapsed) if elapsed else "0:00",
                "remaining": fmt_time(remaining),
                "eta": "0:00",
            }
        # Up-next: starts when the current song ends (plus any requests ahead of it).
        eta = remaining if cur is not None else 0.0
        if eta is not None:
            with self.queue.lock:
                ahead = list(self.queue.requests)
            for q in ahead:
                if q is t:
                    break
                if not q.duration:
                    eta = None
                    break
                eta += q.duration
        return {"elapsed": "0:00", "remaining": t.dur, "eta": fmt_time(eta) if eta else "0:00"}

    def _render(self, template: str, key: str, t: Track) -> str:
        fields = {**t.fields(), **self._time_fields(t)}
        try:
            return template.format(**fields) if template else self.t(key, **fields)
        except Exception:  # a typo in a template must not take down the player-loop thread
            log.exception("bad %s template %r: falling back to the built-in text", key, template)
            return self.t(key, **fields)

    def fmt_now(self, t: Track) -> str:
        return self._render(self.cfg.msg_now, "now_playing", t)

    def fmt_next(self, t: Track) -> str:
        return self._render(self.cfg.msg_next, "up_next", t)

    def now_playing_text(self) -> str:
        """Room reply for !np / "what song is this?": template plus live progress."""
        t = self.current
        if t is None:
            return self.t("nothing_playing").capitalize()
        f = self._time_fields(t)
        progress = f"{f['elapsed']}/{t.dur}" if t.duration else f["elapsed"]
        return f"{self.fmt_now(t)} ({progress})"

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

    def _on_config_reload(self, new_cfg) -> None:
        """Handle config reload from ConfigWatcher."""
        log.info("Config reloaded, applying changes")
        old_cfg = self.cfg
        self.cfg = new_cfg
        self.lang = new_cfg.lang
        # Update volume if changed
        if new_cfg.volume != old_cfg.volume:
            self.set_volume(new_cfg.volume)
        # Update admins set
        self.admins = {a.lower() for a in new_cfg.admins}
        # Update blocked users set
        self.blocked = {b.lower() for b in new_cfg.blocked_users}
        # Update auto-reply settings
        if new_cfg.auto_reply_enabled != old_cfg.auto_reply_enabled:
            if new_cfg.auto_reply_enabled:
                # Start auto-reply loop if it wasn't running
                self._start_auto_reply_loop()
            # If disabled, the loop will exit on its next iteration
        # Update IM auto-reply settings
        if new_cfg.im_auto_reply_enabled != old_cfg.im_auto_reply_enabled:
            if new_cfg.im_auto_reply_enabled:
                # Start IM auto-reply cleanup loop if it wasn't running
                self._start_im_auto_reply_loop()
            # If disabled, the loop will exit on its next iteration
        # Update other dynamic settings
        self.volume = new_cfg.volume
        if hasattr(self.player, "cfg"):
            self.player.cfg = new_cfg  # mpv/yt-dlp paths, audio device, timeouts
        # AI / updater clients snapshot config at construction; rebuild them so
        # edited keys (api key, base URL, enable flags) actually take effect.
        self.refresh_ai()
        self.updater.cfg = new_cfg
        if self.updater.on_available is not None:  # services already started
            self.updater.start()  # no-op unless newly enabled and not yet running
        log.info("Config reload applied successfully")

    def _start_auto_reply_loop(self) -> None:
        """Start the auto-reply loop if not already running."""
        if not self.cfg.auto_reply_enabled:
            return
        # Check if the loop is already running by looking for it in _threads
        for t in self._threads:
            if t.name == "autodj-_auto_reply_loop" and t.is_alive():
                return  # Already running
        t = threading.Thread(
            target=self._auto_reply_loop, daemon=True, name="autodj-_auto_reply_loop"
        )
        self._threads.append(t)
        t.start()
        log.info("Auto-reply loop started via config reload")

    def _start_im_auto_reply_loop(self) -> None:
        """Start the IM auto-reply cleanup loop if not already running."""
        if not self.cfg.im_auto_reply_enabled:
            return
        # Check if the loop is already running
        for t in self._threads:
            if t.name == "autodj-_im_auto_reply_loop" and t.is_alive():
                return  # Already running
        t = threading.Thread(
            target=self._im_auto_reply_loop, daemon=True, name="autodj-_im_auto_reply_loop"
        )
        self._threads.append(t)
        t.start()
        log.info("IM auto-reply cleanup loop started via config reload")

    # ---- chat out -------------------------------------------------------
    def log_chat(self, who: str, text: str):
        with self._chat_lock:
            self.chat_log.append((who, text))
            self.chat_seq += 1
            self._chat_version += 1  # bump version so GUI refreshes on poll
        # Also to the logger (so --log-file / console keeps a trail of every line the bot sent and every
        # line it acted on, even with the GUI closed -- the in-memory chat_log above is lost on restart
        # and was never enough on its own to reconstruct what happened after the fact).
        log.info("chat %s %s: %s", ">>" if who == self.cfg.bot_nick else "<<", who, text)

    def chat_snapshot(self) -> tuple[int, int, list[tuple[str, str]]]:
        """Thread-safe snapshot of (chat_seq, chat_version, chat_log) for the GUI poller.

        Returns:
            (chat_seq, chat_version, chat_log_copy)
        """
        with self._chat_lock:
            return self.chat_seq, self._chat_version, list(self.chat_log)

    def im_snapshot(self) -> tuple[int, int, list[tuple[str, str]]]:
        """Thread-safe snapshot of (im_seq, im_version, im_log) for the IM viewer GUI poller.

        Returns:
            (im_seq, im_version, im_log_copy)
        """
        with self._chat_lock:
            return self.im_seq, self._im_version, list(self.im_log)

    def say(self, text: str) -> bool:
        """Queue a message for sending to the chat room.

        Returns True if the message was queued, False if it was empty after
        cleaning.  Messages are queued even while sends are suspended after
        repeated failures: the suspension only clears on a successful send,
        so refusing to queue would make it permanent.
        """
        text = clean_text(text)
        if not text:
            return False
        self.log_chat(self.cfg.bot_nick, text)
        for i, chunk in enumerate(textwrap.wrap(text, self.cfg.max_msg_len, break_long_words=True)):
            if i and chunk.startswith(self.cfg.prefix):
                chunk = "… " + chunk  # a wrapped continuation must never look like a command
            # _sender() remembers each chunk right before posting it, so its echo
            # is ignored; remembering here too would leave a stale duplicate.
            self.outbox.put(chunk)
        return True

    # The room shows our own lines back to us under the account's nick, which may differ from bot_nick.
    # Remembering what we posted lets us ignore those echoes instead of treating them as commands.
    def _remember_sent(self, text: str):
        """Remember a posted line so its echo from the room is ignored.

        One entry per post: _is_echo() consumes one entry per echo, so posting
        the same line twice must remember it twice or the second echo would be
        handled as a real message (and could reach the AI / command router).
        """
        now = time.monotonic()
        want = norm(text)
        with self._sent_lock:
            while self._sent and self._sent[0][0] < now:
                self._sent.popleft()
            self._sent.append((now + ECHO_TTL, want))

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
        if len(self._delivery_attempts) > MAX_DELIVERY_RECORDS:  # oldest first (dict order)
            for old in list(self._delivery_attempts)[:-MAX_DELIVERY_RECORDS]:
                del self._delivery_attempts[old]
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
        # A dropped message is already reported by NullAdapter.send(): no second warning.
        (log.debug if category == FAIL_DROPPED else log.warning)(
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
                if not getattr(self.adapter, "delivers", True):
                    # No chat connection: the message was discarded, not sent.  Not a
                    # send failure either (that would suspend sending for nothing).
                    self.fail_delivery(attempt_id, FAIL_DROPPED)
                    continue
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

    def prev(self) -> None:
        """Go to the previously played track (from history) and play it now.

        Puts the last completed track back at the front of the request queue
        and stops the current player so the next loop iteration picks it up.
        Safe to call when idle: it just re-queues the last track.
        """
        prev_track = None
        for t in self.history:
            if t is not self.current:
                prev_track = t
                break
        if prev_track is not None:
            # Re-queue at front so it plays next
            # dedupe=False: the duplicate check would silently refuse the
            # re-queue while stop() below still cut the current song.
            self.queue.add_request(prev_track, position=0, dedupe=False)
        self.player.stop()

    def note_request(self) -> None:
        """Record that a user/DJ request just arrived (drives the idle timer)."""
        self._last_user_request_time = time.monotonic()
        if self._autoplay_mode:
            self._autoplay_mode = False
            log.info("Autoplay mode deactivated: new user request received")

    def preempt_unrequested(self) -> bool:
        """Cut the current song only if nobody requested it.

        Request rule: a new request starts *now* when the startup song or an
        autoplay-pool song is playing, but when a requested song is playing it
        waits in the queue (FIFO) until that song ends.  Returns True if cut.
        """
        # A non-requested song that is picked but not yet started is caught by
        # the pre-play check in _play_one_track; the delayed re-check covers a
        # request landing in the few ms between that check and mpv starting.
        self.exec.submit(self._recheck_preempt)
        cur = self.current
        if cur is None or cur.is_request:
            return False
        log.info("request received: cutting non-requested track %r", cur.title)
        self.skip()
        return True

    def _recheck_preempt(self, delay: float = 1.5) -> None:
        if self.stop_evt.wait(delay):
            return
        cur = self.current
        if cur is not None and not cur.is_request and self._has_playable_request():
            log.info("request still waiting behind %r: cutting it", cur.title)
            self.skip()

    def pause(self) -> None:
        if self.current and not self.paused:
            if not self.player.set_pause(True):
                log.warning("pause failed: mpv did not accept the command")
                return
            # Only update pause state if mpv actually accepted the command
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
        # Per-user cooldown check
        now = time.monotonic()
        who = user.lower()
        with self._voteskip_cooldown_lock:
            last_voteskip = self._voteskip_cooldowns.get(
                who, float("-inf")
            )  # never: monotonic starts at boot
            cooldown = getattr(self.cfg, "voteskip_cooldown", 10.0)
            if now - last_voteskip < cooldown:
                remaining = cooldown - (now - last_voteskip)
                return False, self.t("voteskip_cooldown", remaining=round(remaining, 1))
            self._voteskip_cooldowns[who] = now
        self.votes.add(who)
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

            from .tts import TTS_TIMEOUT, synth

            wav = os.path.join(tempfile.gettempdir(), f"autodj-tts-{time.time_ns()}.wav")
            with self._speak_lock:
                try:
                    synth(text, wav, self.cfg)
                    # Duck music volume via IPC, then restore after TTS completes.
                    # play_file handles the restore atomically while IPC is still available.
                    # Use timeout = TTS_TIMEOUT + 30s buffer for playback
                    self.player.play_file(
                        wav,
                        duck_volume=self.cfg.tts_duck,
                        restore_volume=self.volume,
                        timeout=TTS_TIMEOUT + 30.0,
                    )
                except Exception:
                    log.exception("tts failed")
                finally:
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

    def top_requests(self, period: str = "today", limit: int = 5) -> list[dict]:
        """Return the most-requested tracks in the given time window.

        Args:
            period: "today" or "week"
            limit: maximum number of tracks to return

        Returns:
            list of {"title": str, "count": int} sorted from most to least requested
        """
        from pathlib import Path

        counter_path: Path | None = None
        if self.cfg_path:
            counter_path = Path(self.cfg_path).parent / "top_requests.json"
        else:
            counter_path = Path("top_requests.json")

        try:
            data = json.loads(counter_path.read_text(encoding="utf-8-sig"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return []

        now = time.time()
        if period == "today":
            cutoff = now - 86400.0  # 24 hours
        else:  # week
            cutoff = now - 86400.0 * 7

        counts: dict[str, int] = {}
        titles: dict[str, str] = {}
        for entry in data.get("requests", []):
            ts = entry.get("ts", 0)
            if ts < cutoff:
                continue
            src = entry.get("source", "")
            title = entry.get("title", src)
            counts[src] = counts.get(src, 0) + 1
            titles[src] = title

        ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{"title": titles[src], "count": cnt} for src, cnt in ranked]

    def record_request(self, source: str, title: str) -> None:
        """Record a song request for /topm statistics."""
        from pathlib import Path

        counter_path: Path | None = None
        if self.cfg_path:
            counter_path = Path(self.cfg_path).parent / "top_requests.json"
        else:
            counter_path = Path("top_requests.json")

        try:
            with self._stats_lock:  # concurrent requests lost updates / raced on the .tmp
                self._record_request_locked(counter_path, source, title)
        except OSError:
            log.exception("failed to record request for top_requests")

    @staticmethod
    def _record_request_locked(counter_path: Path, source: str, title: str) -> None:
        """Append one request to top_requests.json (caller holds _stats_lock)."""
        try:
            data = json.loads(counter_path.read_text(encoding="utf-8-sig"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            data = {"requests": []}
        if not isinstance(data, dict) or not isinstance(data.get("requests"), list):
            data = {"requests": []}
        data["requests"].append({"source": source, "title": title, "ts": time.time()})
        # Keep only the last 30 days
        cutoff = time.time() - 86400.0 * 30
        data["requests"] = [r for r in data["requests"] if r.get("ts", 0) >= cutoff]
        tmp = counter_path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(counter_path)

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
        if not self.index.contains(p):
            if admin:
                raise UserError(self.t("folders_admin"))
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
                pos, tracks = self._enqueue_requests(tracks, req_id)
                self.wake.set()
                self.note_request()
                self.preempt_unrequested()
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

    def _enqueue_requests(self, tracks: list[Track], req_id: str) -> tuple[int, list[Track]]:
        """Queue *tracks*; return (last position, tracks actually queued).

        Duplicates dropped by ``PlayQueue.add_request`` are not reported as
        queued; ``UserError`` is raised when nothing was added.
        """
        pos, added = 0, []
        for t in tracks:
            n = self.queue.add_request(t)
            if n:
                pos = n
                added.append(t)
                self._log_track(t, "QUEUED", req_id)
        if not added:
            raise UserError(self.t("already_queued"))
        return pos, added

    def load_source(self, src: str, limit: int = 0) -> list[Track]:
        if is_url(src) or SEARCH_PREFIX.match(src):  # "ytsearch20:text" works as an autoplay source
            return self._remote(src, playlist=True, raw_target=True)
        p = Path(src)
        if p.is_dir():
            return scan_folder(p, limit=limit)
        if p.is_file():
            return [local_track(p)]
        raise UserError(self.t("not_found", src=src))

    def load_async(
        self, src: str, announce: bool = True, on_success=None, on_error=None, limit: int = 0
    ):
        def job():
            try:
                tracks = self.load_source(src, limit=limit)
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
                # Keep who asked and whether it was a request: losing is_request let
                # the next request cut (or silently drop) a resolved, requested song.
                res.requester = t.requester
                res.is_request = t.is_request
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
            # Quick check: only proceed if there are search tracks to resolve
            with self.queue.lock:
                candidates = [t for t in self.queue.requests if SEARCH_PREFIX.match(t.source)][:3]
            for cand in candidates:
                if self.stop_evt.is_set():
                    break
                resolved = self._resolve_track_if_search(cand)
                if resolved is not cand:
                    self.queue.replace_request(cand, resolved)
        except Exception:
            log.debug("preload search tracks encountered an issue", exc_info=True)

    def _maybe_preload_search_tracks(self):
        """Submit _preload_search_tracks only if there are search tracks in the queue."""
        with self.queue.lock:
            has_search = any(SEARCH_PREFIX.match(t.source) for t in self.queue.requests)
        if has_search:
            self.exec.submit(self._preload_search_tracks)

    def _load_all(self):
        self._load_library()
        self._load_autoplay_sources()
        self._load_playlist()
        if getattr(self.cfg, "playlist_dir_autoload", False):
            self._load_playlist_dir()
        log.info(
            "autoplay pool: %d tracks; queue: %d requests",
            len(self.queue.pool),
            len(self.queue.requests),
        )
        self.wake.set()
        # Trigger background lookahead resolution for search tracks (only if needed)
        self._maybe_preload_search_tracks()

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
        nxt = self._true_next()
        if self.cfg.announce_next and nxt:
            self.say(self.fmt_next(nxt))

    def _true_next(self) -> Track | None:
        """The track that will really play next (for "up next" lines).

        With a default song configured, an empty request queue means the default
        song (or silence until the idle timeout) comes next, not a pool track.
        """
        with self.queue.lock:
            if self.queue.requests:
                return self.queue.requests[0]
        if (getattr(self.cfg, "default_track", "") or "").strip():
            return None
        return self.queue.peek()

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

    def _pop_next_track(self, now: float | None = None) -> Track | None:
        """Pop the next track to play.

        Order: user requests (FIFO) -> the default song -> the autoplay pool.

        * With ``default_track`` set, the default song plays at startup and,
          once the request queue is empty, as soon as nobody has requested
          anything for ``autoplay_idle_timeout`` seconds (then it repeats until
          the next request).  Until that timeout passes the player waits.
        * If the default song recently failed to play, the autoplay pool is
          used instead so the room never stays silent on a dead link.
        * Without ``default_track`` the autoplay pool plays as before.
        """
        if self.queue.requests:
            # A failed song must not be picked again before a different one.
            # Put skipped items back at the front, in their original order, so
            # they keep their FIFO place once the failure back-off expires.
            skipped: list[Track] = []
            try:
                for _ in range(len(self.queue.requests)):
                    t = self.queue.pop()
                    if t is not None and self._is_recent_failed(t):
                        skipped.append(t)
                        continue
                    self._queue_empty_since = None  # a request plays: idle window restarts later
                    return t
            finally:
                for i, t in enumerate(skipped):
                    self.queue.add_request(t, position=i, dedupe=False)
            # Only recently failed requests are waiting: fall through to the
            # default song / autoplay pool instead of leaving the room silent.
        now = time.monotonic() if now is None else now
        if self._queue_empty_since is None:
            self._queue_empty_since = now  # queue just ran out: idle window starts
        src = (getattr(self.cfg, "default_track", "") or "").strip()
        if src and now >= self._default_failed_until:
            if self._default_due(now):
                return self._default_track_for_play(src)
            return None  # idle timer still running: wait for a request or the timeout
        if self.queue.pool:
            return self.queue.pop_pool()  # autoplay pool: no user request
        return None

    def _is_default_track(self, t: Track) -> bool:
        src = (getattr(self.cfg, "default_track", "") or "").strip()
        meta = self._default_meta
        return bool(src) and (t.source == src or (meta is not None and t.source == meta.source))

    def _default_due(self, now: float) -> bool:
        """True at startup (no request yet), or once the request queue has been
        empty AND nobody has requested anything for ``autoplay_idle_timeout``
        seconds.  Both clocks matter: the window starts when the last requested
        song finished (not when it was requested, which would skip the wait after
        a long song) and a new request restarts it."""
        last = self._last_user_request_time
        if last <= 0:
            return True
        idle = float(getattr(self.cfg, "autoplay_idle_timeout", 30.0))
        start = max(last, self._queue_empty_since if self._queue_empty_since is not None else now)
        return now - start >= idle

    def _default_track_for_play(self, src: str) -> Track:
        """A fresh, non-request Track for the default song.

        * Local file -> played directly (never turned into a YouTube search).
        * URL -> title/duration looked up once and cached.  A failed lookup is
          cached too (retried after 10 min) so the player thread does not block on
          yt-dlp every time the default song repeats; the raw URL is played
          meanwhile (mpv's yt-dlp hook resolves it).
        """
        if not is_url(src) and Path(src).is_file():
            t = local_track(Path(src), "AutoDJ")
            t.is_request = False
            return t
        now = time.monotonic()
        meta = self._default_meta
        if meta is None or meta.source != src:
            meta = None
            if now >= self._default_lookup_retry_at:
                try:
                    found = self._remote(src, user="AutoDJ", playlist=False)
                    if found:
                        meta = found[0]
                except Exception as ex:  # noqa: BLE001 - must never crash the player loop
                    log.warning("default track lookup failed (%s); playing the URL directly", ex)
                if meta is None:
                    self._default_lookup_retry_at = now + 600.0
                else:
                    self._default_meta = meta
        if meta is None:
            return Track(src, src, None, "AutoDJ")
        return Track(meta.source, meta.title, meta.duration, "AutoDJ")

    def _player_loop(self):
        fails = 0  # consecutive tracks that failed to play
        while not self.stop_evt.is_set():
            if not self._mpv_available():
                if fails == 0:
                    log.warning(
                        "mpv not available (mpv_path=%r); waiting for mpv before playing queue",
                        self.cfg.mpv_path,
                    )
                fails += 1
                self.stop_evt.wait(30.0)  # wait 30s before checking again
                continue

            # Honor back-off after consecutive failures: do not start the next
            # track until _backoff_until has passed.
            now = time.monotonic()
            if self._backoff_until > now:
                remaining = self._backoff_until - now
                if self.stop_evt.wait(min(remaining, 1.0)):
                    break
                continue

            if not (getattr(self.cfg, "default_track", "") or "").strip():
                idle_timeout = float(getattr(self.cfg, "autoplay_idle_timeout", 30.0))
                self._check_autoplay_mode(now, idle_timeout)  # pool-only autoplay notice
            t = self._pop_next_track(now)
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
                continue
            # After popping and resolving current, trigger preload for next in queue
            self.exec.submit(self._preload_search_tracks)
            fails = self._play_one_track(t, fails)

    def _mpv_available(self) -> bool:
        # Players without an `available` method (e.g. test fakes) are treated as available.
        if not hasattr(self.player, "available"):
            return True
        return bool(self.player.available())

    def _announce_playback_failure(self, t: Track, fails: int) -> None:
        if fails <= MAX_FAIL_ANNOUNCE:
            # Logged only: the room is never told "cannot play" (owner request;
            # the player simply moves on to the next song).
            log.warning("cannot play %r (%s)", t.title, t.source)
        elif fails == MAX_FAIL_ANNOUNCE + 1:
            log.warning(
                "%d tracks in a row failed to play: not announcing further failures in the room "
                "(check the lines above; run AutoDJ.exe --check)",
                fails - 1,
            )

    def _track_failed(self, t: Track, fails: int) -> None:
        """Mark *t* failed, announce per the back-off policy, then back off.

        Non-blocking: sets ``_backoff_until`` so the player loop pauses before
        the next attempt instead of sleeping here.
        """
        t.state = "FAILED"
        self._log_track(t, "FAILED")
        key = self._track_key(t)
        if key:
            with self._recent_failed_lock:
                self._recent_failed[key] = time.monotonic() + RECENT_FAIL_TTL
        self.current = None
        self._emit("track_failed", t, "playback failed")
        if not t.is_request and self._is_default_track(t):
            # Dead/blocked default link: fall back to the autoplay pool for 10 min
            self._default_failed_until = time.monotonic() + 600.0
            log.warning("default track failed to play; using the autoplay pool for 10 minutes")
        self._announce_playback_failure(t, fails)
        delay = self.fail_delay(fails)
        self._backoff_until = time.monotonic() + delay
        log.info(
            "track failed (%s); backing off %.0fs (fail %d)",
            t.source,
            delay,
            fails,
        )

    @staticmethod
    def _track_key(t: Track) -> str:
        """Normalised identity used to avoid immediately replaying a failed song."""
        return norm(f"{t.title or ''} {t.source or ''}")

    def _is_recent_failed(self, t: Track) -> bool:
        key = self._track_key(t)
        if not key:
            return False
        now = time.monotonic()
        with self._recent_failed_lock:
            for k in [k for k, exp in self._recent_failed.items() if exp <= now]:
                del self._recent_failed[k]
            return key in self._recent_failed

    def _has_playable_request(self) -> bool:
        """True if a queued request exists that is not in its failure back-off.

        Only those may pre-empt an autoplay/default song: a queue holding
        nothing but recently failed requests used to block the pool forever
        (the pool track was popped, then refused because "a request waits").
        """
        with self.queue.lock:
            reqs = list(self.queue.requests)
        return any(not self._is_recent_failed(r) for r in reqs)

    def _try_play(self, t: Track) -> bool:
        try:
            return self.player.play(t.source, self.volume, t.duration)
        except Exception:
            log.exception(
                "cannot start mpv (mpv_path=%r): install mpv and set mpv_path in config.toml",
                self.cfg.mpv_path,
            )
            return False

    def _play_one_track(self, t: Track, fails: int) -> int:
        """Play *t* (repeating if configured) until it completes or the loop stops.

        Returns the updated consecutive-failure count.
        """
        recorded = False
        announced = False  # repeat-one must not re-post "now playing" every loop
        while not self.stop_evt.is_set():
            if not t.is_request and self._has_playable_request():
                # A request arrived while this autoplay/startup song was being
                # picked: requests go first, so don't start it at all.
                log.info("not starting %r: a request is waiting", t.title)
                break
            self.current = t
            t.state = "PLAYING"
            self._log_track(t, "PLAYING")
            self.votes.clear()
            self.paused, self._paused_at, self._paused_total = False, None, 0.0
            self.started_at = time.monotonic()
            if not announced:
                announced = True
                if fails < MAX_FAIL_ANNOUNCE:
                    self._announce(t)
                else:
                    self.exec.submit(self._announce_if_playing, t)
            log.info("playing %s", t.source)
            self._emit("track_start", t)
            if not self._try_play(t):
                fails += 1
                self._track_failed(t, fails)
                return fails
            fails = 0
            if not recorded:
                t.state = "COMPLETED"
                self._log_track(t, "COMPLETED")
                self.history.appendleft(t)
                recorded = True
                self._emit("track_end", t)
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
                # Ignore our own messages: match by normalized nick or by echo detection
                if self._should_ignore_message(msg):
                    continue
                self._dispatch_chat(msg)
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

    def _dispatch_chat(self, msg: ChatMessage) -> None:
        """Route one incoming chat event to its handler."""
        if msg.event == "seen":  # in the room history at startup: present, nothing else
            self._update_participant_count(msg.user)
        elif msg.event == "join":
            self._handle_room_join(msg)
        elif self._is_duplicate_message(msg):
            log.debug(
                "duplicate chat message dropped: user=%r text=%r",
                msg.user,
                msg.text[:60],
            )
            return
        elif msg.is_im:
            self._handle_im(msg)
        else:
            self._handle_room_message(msg)

    def _is_duplicate_message(self, msg: ChatMessage) -> bool:
        """Return True if *msg* is a duplicate of a recently processed line.

        The Camfrog adapter can re-dump a backlog of identical chat lines (for
        example after a reconnect).  Without dedup, each copy is submitted to
        the command router as a separate thread-pool task, and concurrent
        tasks all pass the per-user cooldown check before any of them update
        it -- so the same command runs multiple times at once.  A short
        (3 s) per-user+text window suppresses genuine adapter backlog
        duplicates while still allowing a user to repeat a command after a
        few seconds.
        """
        key = f"{msg.user.lower()}|{norm(msg.text)}"
        now = time.monotonic()
        with self._recent_messages_lock:
            last = self._recent_messages.get(key, 0.0)
            if now - last < 3.0:
                return True
            self._recent_messages[key] = now
            if len(self._recent_messages) > 2000:
                cutoff = now - 10.0
                self._recent_messages = {
                    k: v for k, v in self._recent_messages.items() if v >= cutoff
                }
        return False

    def _should_ignore_message(self, msg: ChatMessage) -> bool:
        """Return True if the message should be ignored (echo or own message).

        An echo also teaches the nick our posts appear under: live 2026-11-23 a
        line of ours that came back slightly changed was taken as the account
        owner speaking, and the bot posted "welcome back, admin Seaza" to itself.
        """
        if norm(msg.user).lower() == self.cfg.bot_nick.lower():
            return True
        if self._is_echo(msg.text):
            nick = norm(msg.user).lower()
            own = self.__dict__.setdefault("_own_nicks", set())
            if nick and nick not in own:
                own.add(nick)
                log.info("own account in the room: %s (never greeted)", msg.user)
            return True
        return False

    def _is_own_account(self, user: str) -> bool:
        return norm(user).lower() in getattr(self, "_own_nicks", ())

    def _never_greet(self, user: str) -> bool:
        """True for nicks no greeting may address: the bot itself, its own account,
        blocked users, ``greeting_ignore`` / ``mic_greeting_ignore`` nicks and room
        bots matching ``greeting_ignore_regex`` (default: a nick ending in "bot").

        Live 2026-11-23..27: the room's own bot ZeazBot was welcomed five times.
        """
        nick = norm(user).lower()
        if not nick or nick in self.blocked or self._is_own_account(user):
            return True
        names = list(self.cfg.greeting_ignore or []) + list(self.cfg.mic_greeting_ignore or [])
        names.append(self.cfg.bot_nick)
        if nick in {norm(s).lower() for s in names if s and s.strip()}:
            return True
        pattern = (self.cfg.greeting_ignore_regex or "").strip()
        if pattern:
            try:
                return re.search(pattern, norm(user)) is not None
            except re.error:  # validated at load; a hot-reloaded bad value must not crash
                log.warning("greeting_ignore_regex is not a valid regex: %r", pattern)
        return False

    def _handle_im(self, msg: ChatMessage) -> None:
        """Handle an instant/private message.

        IMs go to the IM viewer only: they are never added to the room chat log
        and never echoed into the room.

        With ``im_require_room_presence`` (default on) an IM is only acted on
        (auto-reply, plugins, commands) when its sender is in the room, admins
        included: the nickname alone is spoofable from outside the room.
        """
        self._log_im_message(msg)
        if self.cfg.im_require_room_presence and msg.user.lower() not in self._active_room_users:
            log.info("IM from %s not acted on: not in the room", msg.user)
            self._im_join_room_notice(msg.user)
            return
        if self.cfg.im_auto_reply_enabled:
            self._handle_im_message(msg)
        # Emit chat event for plugins
        if self._plugin_manager:
            self._plugin_manager.emit("chat", msg)
        # Process IM commands through the router (like room messages)
        self.exec.submit(self.router.handle, msg)
        # AI: reply to non-command IM messages
        self._ai_handle_im(msg)

    def _im_join_room_notice(self, user: str) -> None:
        """Tell an IM sender outside the room, privately, to join the room first.

        Once per ``im_auto_reply_cooldown`` per user, so a stream of IMs gets one
        answer (our own reply is also read back from the IM window as an echo).
        """
        now = time.monotonic()
        key = f"join:{user.lower()}"
        with self._chat_lock:
            # The cleanup loop only runs with im_auto_reply_enabled: keep this dict
            # bounded on its own (one key per IM sender from outside the room).
            if len(self._im_reply_cooldowns) > 1000:
                cutoff = now - self.cfg.im_auto_reply_cooldown * 2
                for k in [k for k, t in self._im_reply_cooldowns.items() if t < cutoff]:
                    del self._im_reply_cooldowns[k]
            if (
                now - self._im_reply_cooldowns.get(key, float("-inf"))
                < self.cfg.im_auto_reply_cooldown
            ):
                return
            self._im_reply_cooldowns[key] = now
        template = (getattr(self.cfg, "im_join_room_message", "") or "").strip()
        if not template:
            return  # operator turned the reply off
        room = self.cfg.room or ""
        if (
            not room
        ):  # no room name configured: drop the Join link instead of a bare "camfrog:join:"
            template = template.replace("camfrog:join:{room}", "")
        text = _fill(template, room=room, user=user)
        while "  " in text:
            text = text.replace("  ", " ")
        self.send_im(user, text.strip())

    def send_im(self, user: str, text: str) -> bool:
        """Send *text* privately to *user* (never to the room).

        Needs an adapter with ``send_im(user, text)``; otherwise nothing is sent.
        The text is remembered for echo detection, because the IM window shows our
        own reply back without a sender name, and it is shown in the IM viewer.
        """
        text = clean_text(text)
        send = getattr(self.adapter, "send_im", None)
        if not text:
            return False
        if not callable(send):
            log.info("IM to %s not sent: chat adapter cannot send IMs", user)
            return False
        self._remember_sent(text)
        # Camfrog renders camfrog:join:<room> / URLs as links and the IM reader keeps
        # the text before the link: remember that part too, or our own reply comes
        # back as an IM from the user ("IM received: zdevz: please join the room first").
        visible = re.split(r"camfrog:|https?://", text, maxsplit=1)[0].strip()
        if visible and visible != text:
            self._remember_sent(visible)
        try:
            send(user, text)
        except Exception:
            log.exception("Failed to send IM to %s", user)
            return False
        with self._chat_lock:  # IM viewer: outgoing line, same bookkeeping as _log_im_message
            self.im_log.append((f"{self.cfg.bot_nick} → {user}", text))
            if len(self.im_log) > 300:
                del self.im_log[:-300]
            self.im_seq += 1
            self._im_version += 1
        log.info("IM >> %s: %s", user, text)
        return True

    def _ai_handle_im(self, msg: ChatMessage) -> None:
        """AI replies to private messages are intentionally disabled.

        The chat adapter can only post to the public room, so answering an IM
        would broadcast content derived from a private conversation.  Until a
        real ``send_im()`` exists, IMs are never forwarded to the AI provider.
        """
        return

    def _handle_room_message(self, msg: ChatMessage) -> None:
        """Handle a room message (non-IM)."""
        # Per-nick chat rate limiting (non-admins only)
        if msg.user.lower() not in self.admins:
            if not self._check_chat_rate_limit(msg.user):
                log.info("Chat rate limit: dropping message from %s", msg.user)
                return

        self.log_chat(msg.user, msg.text)
        # Emit chat event for plugins
        if self._plugin_manager:
            self._plugin_manager.emit("chat", msg)

        # Track active room users
        self._update_participant_count(msg.user)
        # Camfrog RE integrations: gift announcement + upgrade/payment status alert
        self._handle_re_events(msg)

        # Greet once per visit: on the room's join notice, or (when the client shows no
        # join notice) on the user's first message. Cooldowns stop a second greeting.
        self._greet_user(msg.user)

        # Update last user request time for !play commands (tracked in router)
        self.exec.submit(self.router.handle, msg)
        # "เพลงอะไร / what song is this?" -> answer with the current song
        # (Thai keyword "เพลงอะไร" = "what song is this?")
        if self._answer_np_question(msg):
            return
        # The AI answers only `!ai ask <question>` (commands.py -> ai_ask): ordinary
        # room chat is never sent to the AI provider.

    def _answer_np_question(self, msg: ChatMessage) -> bool:
        """Answer room questions about the current song without a command.

        Matches ``np_question_keywords`` (case-insensitive substring) in
        non-command lines; a room-wide cooldown stops several people asking at
        once from flooding the chat.  Returns True when the message was handled.
        """
        if not getattr(self.cfg, "np_question_reply", False):
            return False
        text = msg.text.strip()
        if not text or text.startswith(self.cfg.prefix):
            return False
        low = text.lower()
        if not any(k and k.lower() in low for k in self.cfg.np_question_keywords):
            return False
        now = time.monotonic()
        if now - self._np_question_last < self.cfg.np_question_cooldown:
            return True  # recently answered: swallow, don't send it to the AI either
        self._np_question_last = now
        self.say(self.now_playing_text())
        return True

    def ai_ask(self, user: str, question: str) -> None:
        """Answer ``!ai ask <question>`` in the room: the only way the AI is used.

        Ordinary room chat is never sent to the AI provider: answering every line
        made the bot reply to other room bots (ZeazBot posts a quote every few
        minutes) and to its own echoed lines.  A per-user cooldown and a cap on
        concurrent provider calls bound room spam and API spend; the network call
        runs on its own pool so it never blocks chat reading or other commands.
        """
        with self._ai_inflight_lock:
            if self._ai_inflight >= AI_MAX_INFLIGHT:
                refused = "ai_busy"
            elif not self.ai.can_reply(user):
                refused = "ai_wait"
            else:
                refused = ""
                self._ai_inflight += 1
        if refused:
            self.say(f"{user}: {self.t(refused)}")
            return
        try:
            self._ai_exec.submit(self._ai_reply, user, question)
        except RuntimeError:  # pool shut down (engine stopping)
            with self._ai_inflight_lock:
                self._ai_inflight -= 1

    def _ai_reply(self, user: str, text: str) -> None:
        try:
            reply = self.ai.chat(text)
            # "<user>: ..." also keeps an answer from ever starting with the command prefix
            self.say(f"{user}: {reply if reply else self.t('chatbot_ai_error')}")
        finally:
            with self._ai_inflight_lock:
                self._ai_inflight -= 1

    def refresh_ai(self) -> None:
        """Rebuild the AI client from the current config (after !ai or reload)."""
        self.ai = AIClient(self.cfg)

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
        with self._chat_lock:  # im_snapshot() reads these under the same lock
            self.im_log.append((msg.user, msg.text))
            if len(self.im_log) > 300:  # bounded: the IM viewer only shows recent history
                del self.im_log[:-300]
            self.im_seq += 1
            self._im_version += 1

    def _handle_room_join(self, msg: ChatMessage) -> None:
        """A user entered the room (``join_line_regex`` matched a room notice)."""
        log.info("room: %s entered", msg.user)
        self._update_participant_count(msg.user)
        self._emit("join", msg.user)
        self._greet_user(msg.user)

    def _greet_user(self, user: str) -> bool:
        """Greet *user* once per cooldown: admins get the admin greeting, everyone else
        the welcome message. Blocked users are never greeted (they are
        silently ignored everywhere else). Returns True if a greeting was sent."""
        if self._never_greet(user):
            return False
        if user.lower() in self.admins and self.cfg.admin_greeting_enabled:
            return self._handle_admin_greeting(ChatMessage(user, ""))
        return self._handle_welcome_message(ChatMessage(user, ""))

    def _handle_admin_greeting(self, msg: ChatMessage) -> bool:
        """Greet an admin who entered the room (or spoke first), if enabled."""
        if not self.cfg.admin_greeting_enabled:
            return False
        if msg.user.lower() not in self.admins or self._never_greet(msg.user):
            return False
        now = time.monotonic()
        last_greeting = self._admin_greeting_cooldowns.get(msg.user.lower(), float("-inf"))
        if now - last_greeting < self.cfg.admin_greeting_cooldown:
            return False
        greeting = _fill(
            self.cfg.admin_greeting_message, admin=msg.user, user=msg.user, room=self.cfg.room
        )
        self.say(greeting)
        self._admin_greeting_cooldowns[msg.user.lower()] = now
        log.info("Sent admin greeting to %s", msg.user)
        return True

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
    # A mic *notice* is a whole line "<nick> <phrase>", e.g. "Seaza is now speaking" or
    # "Seaza กำลังรับไมค์" (Thai: "Seaza is now taking the mic").  The nick is required and
    # only whole lines match, so ordinary chat such as "who is the dj?" never triggers it.
    _MIC_NOTICE_RE = re.compile(
        r"^(?P<nick>\S{1,30})\s+(?:"
        r"is\s+now\s+speaking"
        r"|has\s+the\s+mic"
        r"|is\s+the\s+dj"
        r"|receiving\s+mic"
        r"|took\s+the\s+mic"
        r"|กำลังรับไมค์"
        r"|กำลังพูด"
        r")\.?$",
        re.IGNORECASE,
    )
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
        if self.cfg.mic_greeting_enabled:
            mic_nick = self._mic_notice_nick(nick, body)
            if mic_nick:
                self._announce_mic_greeting(mic_nick)
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

    # A status *notice* is a whole line of one of these shapes ("bob is now away",
    # "bob is an admin").  Matching a bare substring announced ordinary chat:
    # "anyway" -> away, a quote mentioning an "owner" -> "X is the room owner".
    _STATUS_NOTICE_RE = re.compile(
        r"^(?:\S{1,30}\s+)?is\s+(?:now\s+)?(?P<state>online|away|busy|invisible)\.?$"
        r"|^(?:\S{1,30}\s+)?is\s+(?:an?\s+|the\s+(?:room\s+)?)(?P<role>admin|moderator|owner)\.?$",
        re.IGNORECASE,
    )

    def _is_status_indicator(self, body: str) -> str | None:
        """Message key for a status notice line (whole line, see _STATUS_NOTICE_RE), else None."""
        m = self._STATUS_NOTICE_RE.match(body.strip())
        if not m:
            return None
        word = (m.group("state") or m.group("role")).lower()
        return self._STATUS_INDICATOR_KEYWORDS.get(word)

    def _mic_notice_nick(self, sender: str, body: str) -> str | None:
        """Return the nick a Camfrog mic/DJ notice names, or None if *body* is not one.

        A user can type "Bob is now speaking" in chat; that only counts when the
        sender is Bob, the line has no sender (a system notice), or the sender is a
        room bot listed in ``mic_notice_senders`` (e.g. ZeazBot posts
        "Seaza กำลังรับไมค์" when Seaza takes the mic).  Anyone else cannot get
        the bot to announce somebody else as the DJ.
        """
        m = self._MIC_NOTICE_RE.match(body.strip())
        if not m:
            return None
        named = m.group("nick")
        who = norm(sender).lower() if sender else ""
        if who and who != norm(named).lower():
            trusted = {norm(s).lower() for s in (self.cfg.mic_notice_senders or []) if s.strip()}
            if who not in trusted:
                return None
        return named

    def _announce_mic_greeting(self, nick: str) -> None:
        """Greet a user who just received the room mic (became the DJ)."""
        if self._never_greet(nick):
            return  # room bots, the bot itself, the account AutoDJ streams from, ...
        now = time.monotonic()
        last = self._mic_greeting_cooldowns.get(nick.lower(), float("-inf"))
        if now - last < self.cfg.mic_greeting_cooldown:
            return
        template = (self.cfg.mic_greeting_message or "").strip()
        if template:
            try:
                text = template.format(user=nick)
            except (KeyError, IndexError, ValueError):
                log.warning("mic_greeting_message is not a valid template; using the default")
                text = self.t("mic_greeting", user=nick)
        else:
            text = self.t("mic_greeting", user=nick)
        self.say(text)
        self._mic_greeting_cooldowns[nick.lower()] = now
        log.info("Sent mic greeting to %s", nick)

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

    def _handle_welcome_message(self, msg: ChatMessage) -> bool:
        """Welcome a user who entered the room (or spoke first) in the room.

        Only for non-IM messages. Rate-limited per user using welcome_message_cooldown
        to avoid spam. Thread-safe per-user cooldown tracking. ``{user}`` and ``{room}``
        in the text are filled in. Returns True if the welcome was sent (or scheduled).

        If ``welcome_message_delay`` is greater than 0, the welcome is sent by a
        dedicated daemon timer after the delay instead of immediately.
        """
        if not self.cfg.welcome_message_enabled or msg.is_im or self._never_greet(msg.user):
            return False
        now = time.monotonic()
        key = f"welcome:{msg.user.lower()}"
        cooldown = getattr(self.cfg, "welcome_message_cooldown", 3600.0)
        should_send = False
        welcome_text = ""
        with self._chat_lock:
            last_welcome = self._welcome_cooldowns.get(key, float("-inf"))  # never sent
            if now - last_welcome >= cooldown:
                welcome_text = _fill(
                    self.cfg.welcome_message_message, user=msg.user, room=self.cfg.room
                )
                if not self.cfg.room:  # no room name configured: no "into  station" gap
                    while "  " in welcome_text:
                        welcome_text = welcome_text.replace("  ", " ")
                    welcome_text = welcome_text.strip()
                should_send = True
                self._welcome_cooldowns[key] = now
        if should_send:
            delay = getattr(self.cfg, "welcome_message_delay", 0.0)
            if delay and delay > 0:
                timer = threading.Timer(delay, self._send_welcome_after_delay, args=(welcome_text,))
                timer.daemon = True
                with self._welcome_timers_lock:
                    self._welcome_timers.add(timer)
                timer.start()
            else:
                self.say(welcome_text)
                log.info("Sent welcome message to %s", msg.user)
        return should_send

    def _send_welcome_after_delay(self, text: str) -> None:
        """Send a delayed welcome from its daemon timer, never from the worker pool."""
        try:
            with self._welcome_timers_lock:
                self._welcome_timers.discard(threading.current_thread())
            if self.stop_evt.is_set():
                return
            self.say(text)
            log.info("Sent delayed welcome message")
        except Exception:  # engine shutting down / send failure must not kill the timer
            log.exception("failed to send delayed welcome message")

    def _emit(self, event: str, *args) -> None:
        """Forward an engine event to loaded plugins (never raises)."""
        if self._plugin_manager:
            self._plugin_manager.emit(event, *args)

    def plugin_command(self, name: str, user: str, args: str, admin: bool) -> bool:
        """Offer a command no built-in handles to the plugins; True if one did."""
        if not self._plugin_manager:
            return False
        for pname, plugin in list(self._plugin_manager.plugins.items()):
            try:
                if plugin.on_command(name, user, args, admin):
                    return True
            except Exception:
                log.exception("plugin %s failed on command %s", pname, name)
        return False

    def _start_optional_services(self) -> None:
        """Config hot reload and the webhook server, when enabled in config."""
        if (
            getattr(self.cfg, "config_hot_reload", False)
            and self.cfg_path
            and not self._config_watcher
        ):
            try:
                from .config_watcher import ConfigWatcher

                watcher = ConfigWatcher(str(self.cfg_path))
                watcher.on_change(self._on_config_reload)
                watcher.start(initial_config=self.cfg)
                self._config_watcher = watcher
            except Exception as ex:  # noqa: BLE001 - optional feature must not stop the bot
                log.warning("config hot reload unavailable: %s", ex)
        if getattr(self.cfg, "webhook_enabled", False) and not self._webhook_server:
            secret = getattr(self.cfg, "webhook_secret", "") or ""
            if len(secret) < 16:
                log.error(
                    "webhook_enabled but webhook_secret is shorter than 16 chars: not started"
                )
                return
            try:
                from .webhook.models import WebhookConfig
                from .webhook.server import WebhookServer
            except ImportError as ex:
                log.error("webhook needs the 'webhook' extra (fastapi, uvicorn): %s", ex)
                return
            wcfg = WebhookConfig(
                enabled=True,
                port=int(self.cfg.webhook_port),
                secret=secret,
                host=self.cfg.webhook_host,
                rate_limit_per_ip=int(self.cfg.webhook_rate_limit_per_ip),
                cors_origins=list(self.cfg.webhook_cors_origins),
            )
            self._webhook_server = WebhookServer(wcfg, self)

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
        self._start_optional_services()
        # Start webhook server if enabled
        if self._webhook_server:
            webhook_server = self._webhook_server

            # serve_blocking() runs uvicorn to completion on its own event loop
            # (the old start() only created a task and the loop exited at once).
            t = threading.Thread(
                target=webhook_server.serve_blocking, daemon=True, name="autodj-webhook"
            )
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

        # Start auto-update checker (owns its thread; opt-in via
        # auto_update_enabled — no network traffic to GitHub otherwise).
        self.updater.on_available = self._announce_update
        self.updater.start()

    def _auto_update_check(self) -> None:
        """One-shot update check + room announcement (opt-in only)."""
        if not self.updater.enabled:
            return
        try:
            release = self.updater.check_for_update()
            if release:
                self._announce_update(release)
        except Exception:  # noqa: BLE001 - auto-update must never crash
            log.exception("auto-update check failed")

    def _announce_update(self, release: dict) -> None:
        """Announce a newly available release in the room."""
        try:
            if release:
                self.say(
                    self.t(
                        "update_available",
                        version=release["tag"],
                        current=__import__("autodj", fromlist=["__version__"]).__version__,
                        url=release["html_url"],
                    )
                )
        except Exception:  # noqa: BLE001 - auto-update must never crash
            log.exception("auto-update check failed")

    def _auto_reply_path(self) -> str:
        """ads-list.json, resolved against the config file's folder."""
        from . import ads_list

        return ads_list.resolve_path(self.cfg.auto_reply_file, self.cfg_path)

    @staticmethod
    def _auto_reply_reload(path: str, stamp: object) -> tuple[object, list[str]] | None:
        """(new stamp, shuffled messages) when *path* changed since *stamp*, else None."""
        from . import ads_list

        now_stamp = ads_list.mtime(path)
        if now_stamp == stamp:
            return None
        messages = ads_list.load(path)
        if messages:
            log.info("auto-reply: %d message(s) loaded from %s", len(messages), path)
        else:
            log.warning("auto-reply enabled but no messages found in %r", path)
        random.shuffle(messages)
        return now_stamp, messages

    def _auto_reply_loop(self):
        """Send scheduled auto-reply messages from ads-list.json to the room.

        Messages are sent every auto_reply_interval seconds (minimum 60s) in a
        shuffled rotation: every message once before any repeats. The file is read
        again whenever it changes (the GUI's ads editor saves it), and an empty or
        missing file keeps the loop waiting instead of ending it. A slot is skipped
        while the Camfrog room chat is not open, so no ad is dropped.
        """
        if not self.cfg.auto_reply_enabled:
            log.debug("auto-reply disabled; loop not started")
            return
        path = self._auto_reply_path()
        stamp: object = object()  # never equal to a real mtime: forces the first load
        shuffled: list[str] = []
        idx = 0
        while not self.stop_evt.is_set():
            reloaded = self._auto_reply_reload(path, stamp)
            if reloaded is not None:
                (stamp, shuffled), idx = reloaded, 0
            # Wait between messages (minimum 60s), but wake up immediately on shutdown
            if self.stop_evt.wait(max(60.0, self.cfg.auto_reply_interval)):
                break
            if self.stop_evt.is_set() or not shuffled:
                continue
            if not bool(getattr(self.adapter, "room_ready", True)):
                # Live 2026-11-27: ads were logged "sent" while the room was closed and
                # the adapter dropped them; keep this message for the next slot instead.
                log.info("auto-reply skipped: the Camfrog room chat is not open")
                continue
            msg = shuffled[idx]
            idx += 1
            if idx >= len(shuffled):  # a full cycle: reshuffle
                random.shuffle(shuffled)
                idx = 0
            try:
                self.say(msg)
                log.info("auto-reply sent: %r", msg[:60])
            except Exception:
                log.exception("auto-reply send failed")

    @staticmethod
    def _load_auto_reply_messages(path: str) -> list[str]:
        """Messages in ads-list.json (see :mod:`autodj.ads_list` for the formats)."""
        from . import ads_list

        return ads_list.load(path)

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
        """Handle incoming IM (private message) and send auto-reply if enabled.

        The reply is sent privately through the adapter's optional
        ``send_im(user, text)``. Adapters without a private channel get no reply:
        an IM conversation is never posted into the room.
        """
        if not self.cfg.im_auto_reply_enabled:
            return
        if not msg.is_im:
            return
        user = msg.user.lower()
        now = time.monotonic()
        reply_text = self.cfg.im_auto_reply_message
        if not reply_text:
            return
        # Decide and claim the cooldown under the lock, but send OUTSIDE it:
        # say() -> log_chat() takes the same non-reentrant _chat_lock, so
        # calling it here deadlocked the chat loop on the first IM, and the
        # GUI (chat_snapshot) froze with it.
        with self._chat_lock:  # protect _im_reply_cooldowns across chat loop and cleanup loop
            last_reply = self._im_reply_cooldowns.get(user, float("-inf"))  # never replied
            if now - last_reply < self.cfg.im_auto_reply_cooldown:
                log.debug("IM auto-reply on cooldown for %s", user)
                return
            self._im_reply_cooldowns[user] = now
        if self.send_im(msg.user, reply_text):
            log.info("Sent IM auto-reply to %s", msg.user)

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
                cutoff = now - _CHAT_RATE_LIMIT_WINDOW
                with self._chat_rate_lock:
                    for nick in list(self._chat_rate_window):
                        window = self._chat_rate_window[nick]
                        while window and window[0] <= cutoff:
                            window.popleft()
                        if not window:
                            del self._chat_rate_window[nick]
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
            im_seq, im_version, im_entries = self.im_snapshot()
            checks["im_viewer"] = {
                "ok": True,
                "seq": im_seq,
                "version": im_version,
                "entries": len(im_entries),
            }
        except Exception as ex:  # noqa: BLE001
            checks["im_viewer"] = {"ok": False, "details": str(ex)}
            ok = False

        return {"ok": ok, "checks": checks, "timestamp": time.monotonic()}

    # ---- admin: mic mute / unmute ----------------------------------------

    def mute_mic(self, muted: bool):
        """Mute or unmute AutoDJ's music output by setting the player volume.

        Despite the historical name, this does NOT mute the Camfrog microphone
        device; it only silences the bot's own playback. Restores the previous
        volume on unmute.
        """
        if muted:
            self._mic_prev_volume = self.volume
            self.set_volume(0)
            self.mute_enabled = True
            log.info("Music output muted by admin (Camfrog mic is not affected)")
        else:
            self.set_volume(getattr(self, "_mic_prev_volume", 70))
            self.mute_enabled = False
            log.info("Music output unmuted by admin")

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

    def _send_punish(self, nick: str, kind: str) -> None:
        self.say(f"/punish {nick}")
        log.info("Punished %s: %s", kind, nick)

    def punish_user(self, nick: str) -> None:
        """Punish a user via Camfrog /punish command."""
        self._send_punish(nick, "user")

    def punish_bot(self, nick: str) -> None:
        """Punish a bot via Camfrog /punish command."""
        self._send_punish(nick, "bot")

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
        with self._welcome_timers_lock:
            for timer in tuple(self._welcome_timers):
                timer.cancel()
            self._welcome_timers.clear()
        self.player.stop()
        # Stop config watcher
        if self._config_watcher:
            self._config_watcher.stop()
            self._config_watcher = None
        # Unload plugins
        if self._plugin_manager:
            self._plugin_manager.unload_plugins()
        # Stop webhook server (thread-safe flag; uvicorn exits its own loop)
        if self._webhook_server:
            try:
                self._webhook_server.request_stop()
            except Exception:
                log.exception("Failed to stop webhook server")
        self.adapter.close()
        self.exec.shutdown(wait=False, cancel_futures=True)
        self._ai_exec.shutdown(wait=False, cancel_futures=True)
        # Shutdown TTS worker
        from .tts import shutdown_tts

        shutdown_tts()
        # Shutdown library caches
        from .library import shutdown_library_caches

        shutdown_library_caches()
        # Stop auto-update checker
        self.updater.stop()
        # Join daemon threads with a timeout so shutdown does not hang forever.
        for t in self._threads:
            if t.is_alive():
                t.join(timeout=5.0)
