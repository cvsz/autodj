from __future__ import annotations

import itertools
import json
import logging
import os
import queue
import textwrap
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .commands import Router
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
from .models import Track, UserError, YtdlpMissingError
from .player import MpvPlayer
from .playlist import PlaylistStore, load_playlist
from .playqueue import PlayQueue
from .textutil import clean_text, norm

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

_req_ids = itertools.count()  # global request ID counter


class Engine:
    def __init__(self, cfg, adapter, player=None, index=None, cfg_path=None):
        self.cfg, self.adapter = cfg, adapter
        self.cfg_path = cfg_path
        self.lang = cfg.lang
        self.player = player or MpvPlayer(cfg)
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
        self.stop_evt = threading.Event()
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

    def say(self, text: str):
        text = clean_text(text)
        if not text:
            return
        self.log_chat(self.cfg.bot_nick, text)
        for i, chunk in enumerate(textwrap.wrap(text, self.cfg.max_msg_len, break_long_words=True)):
            if i and chunk.startswith(self.cfg.prefix):
                chunk = "… " + chunk  # a wrapped continuation must never look like a command
            self.outbox.put(chunk)

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
                log.info("send ok: %r", m)
            except (OSError, RuntimeError) as ex:
                self.fail_delivery(attempt_id, FAIL_DELIVERY)
                log.warning("send failed (%s); retrying once in 2s", ex)
                self.stop_evt.wait(2.0)
                if self.stop_evt.is_set():
                    break
                try:
                    self.adapter.send(m)
                    self.confirm_delivery(attempt_id)
                    log.info("send retry ok: %r", m)
                except Exception:
                    self.fail_delivery(attempt_id, FAIL_DELIVERY)
                    log.exception("send retry failed too, dropped: %r", m)
            self.stop_evt.wait(self.cfg.send_interval)  # flood control (wakes up at shutdown)

    # ---- controls -------------------------------------------------------
    def skip(self):
        self.player.stop()

    def pause(self):
        if self.current and not self.paused:
            if (
                self.player.set_pause(True) is False
            ):  # mpv's control pipe is not ready (yet): state stays truthful
                log.warning("pause failed: mpv did not accept the command")
                return
            self.paused, self._paused_at = True, time.monotonic()

    def resume(self):
        if self.paused:
            if self.player.set_pause(False) is False:
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

    def set_volume(self, v: int):
        self.volume = max(0, min(100, int(v)))
        self.player.set_volume(self.volume)

    def speak(self, text: str):
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
                    self.player.set_volume(self.cfg.tts_duck)
                    self.player.play_file(wav)
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
        on_success=None,
        on_error=None,
    ):
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
        on_success=None,
        on_error=None,
        limit: int = 0,
        max_dirs: int = 0,
    ):
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
                    log.info("playlist dir: loaded %d track(s) from %s", len(dir_tracks), pl_file)
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
            t = self.queue.pop()
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
            self.say(self.t("cannot_play", title=t.title))
        elif fails == MAX_FAIL_ANNOUNCE + 1:
            log.warning(
                "%d tracks in a row failed to play: not announcing further failures in the room "
                "(check the lines above; run AutoDJ.exe --check)",
                fails - 1,
            )

    def _track_failed(self, t: Track, fails: int) -> None:
        """Mark *t* failed, announce per the back-off policy, then back off."""
        t.state = "FAILED"
        self._log_track(t, "FAILED")
        self.current = None
        self._announce_playback_failure(t, fails)
        self.stop_evt.wait(self.fail_delay(fails))  # back off: never spin on a broken setup

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
                if norm(msg.user).lower() == self.cfg.bot_nick.lower() or self._is_echo(msg.text):
                    continue
                self.log_chat(msg.user, msg.text)
                self.exec.submit(self.router.handle, msg)
        except Exception:
            if (
                not self.stop_evt.is_set()
            ):  # at shutdown the adapter/executor going away is expected
                log.exception("chat loop ended")
        finally:
            self.chat_done.set()

    def start(self):
        """Non-blocking: used by the GUI."""
        if hasattr(self.player, "available") and not self.player.available():
            log.error(
                'mpv not found (mpv_path=%r). Install mpv and set mpv_path = "C:/mpv/mpv.exe" '
                "in config.toml; nothing will play until then.",
                self.cfg.mpv_path,
            )
        for fn in (
            self._sender,
            self._player_loop,
            self._load_all,
            self._chat_loop,
            self._auto_reply_loop,
        ):
            t = threading.Thread(target=fn, daemon=True, name=f"autodj-{fn.__name__}")
            self._threads.append(t)
            t.start()

    def _auto_reply_loop(self):
        """Send scheduled auto-reply messages from ads-list.json to the room."""
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
        idx = 0
        interval = max(60.0, self.cfg.auto_reply_interval)  # minimum 60s to avoid spam
        while not self.stop_evt.is_set():
            # Wait between messages, but wake up immediately on shutdown
            if self.stop_evt.wait(interval):
                break
            if self.stop_evt.is_set():
                break
            msg = messages[idx % len(messages)]
            idx += 1
            try:
                self.say(msg)
                log.info("auto-reply sent: %r", msg[:60])
            except Exception:
                log.exception("auto-reply send failed")

    @staticmethod
    def _load_auto_reply_messages(path: str) -> list[str]:
        """Load messages from ads-list.json. Returns a list of message strings."""
        try:
            data = json.loads(Path(path).read_text("utf-8-sig"))
        except FileNotFoundError:
            log.debug("auto-reply file %r not found", path)
            return []
        except Exception:
            log.warning("cannot read auto-reply file %r", path, exc_info=True)
            return []
        entries = data.get("messages", []) if isinstance(data, dict) else data
        if not isinstance(entries, list):
            return []
        return [str(m) for m in entries if m]

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

    def shutdown(self):
        self.stop_evt.set()
        self.wake.set()
        self.player.stop()
        self.adapter.close()
        self.exec.shutdown(wait=False, cancel_futures=True)
        # Join daemon threads with a timeout so shutdown does not hang forever.
        for t in self._threads:
            if t.is_alive():
                t.join(timeout=5.0)
