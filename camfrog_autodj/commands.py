from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .adapters.base import ChatMessage
    from .engine import Engine

from .models import UserError

log = logging.getLogger("autodj")
COMMANDS: dict[str, tuple] = {}


def command(*names, admin=False):
    def deco(fn):
        for n in names:
            if n in COMMANDS:  # a silent overwrite would make one command unreachable
                raise ValueError(f"command name {n!r} is registered twice")
            COMMANDS[n] = (fn, admin)
        return fn

    return deco


class Router:
    def __init__(self, engine):
        self.e = engine
        self.last: dict[str, float] = {}
        self.user_requests: dict[str, list[float]] = {}
        self._lock: threading.Lock = (
            threading.Lock()
        )  # guards last + user_requests (TOCTOU protection)

    def is_admin(self, msg) -> bool:
        # NOTE: Nickname-based authorization is spoofable — any user can adopt an
        # operator's nick and gain admin privileges. Prefer immutable authenticated
        # account identifiers where the chat protocol supports them.
        # `msg.local` is trusted only for local/development execution.
        if msg.local:
            return True
        if not self.e.admins:
            # Empty admin list -> fail-closed: no nickname-based admin access.
            return False
        return msg.user.lower() in self.e.admins

    def handle(self, msg):
        e, p = self.e, self.e.cfg.prefix
        text = msg.text.strip()
        is_im = getattr(msg, "is_im", False)
        parsed = self._parse_command(text, p, is_im)
        if parsed is None:
            return
        name, arg = parsed
        entry = COMMANDS.get(name.lower())
        admin = self.is_admin(msg)
        self._log_command(msg, name, arg, admin, is_im, p)
        if not entry:
            return
        fn, need_admin = entry

        # IM Security: require user to be in the room (seen in chat) to use IM commands
        if is_im and not admin and getattr(e.cfg, "im_require_room_presence", True):
            active_users = getattr(e, "_active_room_users", None)
            if active_users is not None and msg.user.lower() not in active_users:
                log.info("IM command %s from %s rejected: user not in room", name, msg.user)
                e.say(f"{msg.user}: {e.t('im_user_not_in_room')}")
                return

        if not admin and msg.user.lower() in e.blocked:
            self._log_blocked(msg, is_im)
            return

        if need_admin and not admin:
            e.say(f"{msg.user}: {e.t('admin_only')}")
            return

        now = time.monotonic()
        if not admin and not self._within_limits(msg, name, now, is_im):
            return

        try:
            fn(e, msg, arg.strip(), admin)
        except UserError as ex:
            e.say(f"{msg.user}: {ex}")
        except Exception:
            log.exception("command failed: %s", text)
            e.say(f"{msg.user}: {e.t('error')}")

    def _log_command(self, msg, name: str, arg: str, admin: bool, is_im: bool, prefix: str):
        if is_im:
            log.info(
                "im command %s (%s) from %s%s", name, arg, msg.user, ", admin" if admin else ""
            )
        else:
            log.info(
                "command %s%s (%s) from %s%s",
                prefix,
                name,
                arg,
                msg.user,
                ", admin" if admin else "",
            )

    def _is_play_command_blocked_in_room(self, msg, name: str, is_im: bool, admin: bool) -> bool:
        """Play/Request commands only work via IM for non-admins."""
        play_commands = ("play", "request", "req", "p", "เล่น", "ขอเพลง", "เล่นเพลง")
        if name.lower() in play_commands and not is_im:
            if not admin:
                self.e.say(f"{msg.user}: {self.e.t('im_only_command')}")
                return True
        return False

    def _log_blocked(self, msg, is_im: bool):
        log.info("blocked: ignoring %s's command from %s", msg.user, "IM" if is_im else "room")

    def _parse_command(self, text: str, p: str, is_im: bool) -> tuple[str, str] | None:
        """Return (name, arg) when *text* is a command, else None."""
        if is_im:
            # IM / private message: no prefix required, but still subject to cooldown/limits
            name, _, arg = text.partition(" ")
            return name, arg
        # Room message: must start with the command prefix
        if not text.startswith(p):
            return None
        name, _, arg = text[len(p) :].partition(" ")
        return name, arg

    def _within_limits(self, msg, name: str, now: float, is_im: bool) -> bool:
        """Cooldown + per-user sliding-window request limit.

        Returns False when the command must be dropped (a reply is sent for rate limits).
        Thread-safe: all reads/writes to self.last and self.user_requests are guarded
        by self._lock to prevent TOCTOU races under concurrent command handling.
        """
        e = self.e
        who = (
            msg.user.lower()
        )  # "Bob" and "bob" are one person: changing case must not dodge the cooldown

        with self._lock:
            # Cooldown check
            if now - self.last.get(who, -1e9) < e.cfg.cooldown:
                log.info(
                    "cooldown: dropping %s's command from %s (%.1fs to go)",
                    msg.user,
                    "IM" if is_im else "room",
                    e.cfg.cooldown - (now - self.last[who]),
                )
                return False

            # Prune expired entries to prevent unbounded memory growth (memory leak fix)
            window = getattr(e.cfg, "rate_limit_window", 300.0)
            cutoff = now - window
            expired = [
                u for u, ts_list in self.user_requests.items() if all(t < cutoff for t in ts_list)
            ]
            for u in expired:
                del self.user_requests[u]

            # Also prune stale cooldown entries (last dict) - keep only entries within 2x window
            cooldown_cutoff = now - window * 2
            stale_last = [u for u, t in self.last.items() if t < cooldown_cutoff]
            for u in stale_last:
                del self.last[u]

            # Sliding window request limit per user
            if name.lower() in ("play", "request", "req", "p", "เล่น", "ขอเพลง", "เล่นเพลง"):
                limit = getattr(e.cfg, "user_request_limit", 5)
                reqs = [t for t in self.user_requests.get(who, []) if now - t < window]
                if len(reqs) >= limit:
                    log.info(
                        "rate limit: user %s exceeded %d requests in %.0fs",
                        who,
                        limit,
                        window,
                    )
                    e.say(f"{msg.user}: {e.t('max_requests', n=limit)}")
                    return False
                reqs.append(now)
                self.user_requests[who] = reqs
            self.last[who] = now
            return True


def _line(t) -> str:
    return f"{t.title} [{t.dur}] ({t.requester})"


@command("help", "commands", "ช่วยเหลือ")
def _help(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    p = e.cfg.prefix
    e.say(e.t("help_base", p=p) + (e.t("help_admin", p=p) if admin else ""))


@command("play", "request", "req", "p", "เล่น", "ขอเพลง", "เล่นเพลง")
def _play(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    c, p = e.cfg, e.cfg.prefix
    if not a:
        raise UserError(e.t("usage_play", p=p))
    if not admin:
        _assert_queue_capacity(e, m.user)
    tracks = e.resolve(a, m.user, admin)
    if not tracks:
        raise UserError(e.t("nothing_found"))
    if not admin:
        tracks = _validate_non_admin_track(e, c, tracks)
    pos = 0
    with e.queue.lock:  # the lookup above can take seconds: re-check now, atomically with the add
        if not admin:
            _assert_queue_capacity(e, m.user)
            _assert_not_already_queued(e, tracks[0])
        for t in tracks:
            pos = e.queue.add_request(t, position=0)  # insert at front: play next immediately
    e.wake.set()
    # Update last user request time for autoplay idle timeout
    e._last_user_request_time = time.monotonic()
    # Exit autoplay mode immediately when user makes a request
    if e._autoplay_mode:
        e._autoplay_mode = False
        log.info("Autoplay mode deactivated: new user request received")
    if e.playlist:  # promised by the playlist docs / config: chat requests are saved too (feeds !last and the pool)
        e.playlist.add(tracks)
    if len(tracks) == 1:
        e.say(e.t("queued_one", pos=pos, title=tracks[0].title, dur=tracks[0].dur, user=m.user))
    else:
        e.say(e.t("queued_many", n=len(tracks), user=m.user))


def _assert_queue_capacity(e, user: str) -> None:
    c = e.cfg
    if len(e.queue.requests) >= c.max_queue:
        raise UserError(e.t("queue_full"))
    if e.queue.count_by(user) >= c.max_requests_per_user:
        raise UserError(e.t("max_requests", n=c.max_requests_per_user))


def _validate_non_admin_track(e, c, tracks: list) -> list:
    tracks = tracks[:1]
    t = tracks[0]
    if t.duration is None and t.source.startswith("http"):
        raise UserError(e.t("live_not_allowed"))
    if t.duration and t.duration > c.max_duration:
        raise UserError(e.t("too_long", m=c.max_duration // 60))
    return tracks


def _assert_not_already_queued(e, t) -> None:
    # e.current is read under the queue lock to avoid a data race with _player_loop
    src = t.source
    current_source = e.current.source if e.current else None
    if (current_source == src) or any(r.source == src for r in e.queue.requests):
        raise UserError(e.t("already_queued"))


@command("last", "requested", "ขอล่าสุด")
def _last(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    items = e.recent_requests(5)
    if not items:
        raise UserError(e.t("requested_none"))
    e.say(e.t("last_head") + " | ".join(f"{t.requester}: {t.title}" for t in items))


@command("np", "nowplaying", "เพลงนี้")
def _np(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    t = e.current
    e.say(e.fmt_now(t) if t else e.t("nothing_playing").capitalize())


@command("next", "upnext", "ถัดไป")
def _next(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    t = e.queue.peek()
    e.say(e.fmt_next(t) if t else e.t("nothing_queued"))


@command("queue", "q", "คิว")
def _queue(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    with e.queue.lock:
        items = list(e.queue.requests)
    if not items:
        e.say(e.t("queue_empty"))
        return
    shown = " | ".join(f"{i}) {_line(t)}" for i, t in enumerate(items[:5], 1))
    e.say(shown + (" " + e.t("queue_more", n=len(items) - 5) if len(items) > 5 else ""))


@command("skip", "ข้าม")
def _skip(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    cur = e.current
    if not cur:
        raise UserError(e.t("nothing_playing"))
    if admin or cur.requester.lower() == m.user.lower():
        e.skip()
        e.say(e.t("skipped"))
    else:
        raise UserError(e.t("skip_denied", p=e.cfg.prefix))


@command("voteskip", "vs", "โหวตข้าม")
def _voteskip(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    if not e.current:
        raise UserError(e.t("nothing_playing"))
    e.votes.add(m.user.lower())
    n = len(e.votes)
    need = e.cfg.voteskip_threshold
    if getattr(e.cfg, "voteskip_dynamic", False):
        participants = getattr(e, "participant_count", 0)
        if participants > 0:
            pct = getattr(e.cfg, "voteskip_dynamic_pct", 30)
            need = max(1, round((participants * pct) / 100.0))
    if n >= need:
        e.skip()
        e.say(e.t("vote_passed", n=n, need=need))
    else:
        e.say(e.t("vote_progress", n=n, need=need))


@command("remove", "rm", "ลบ")
def _remove(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    if not a.isascii() or not a.isdigit():  # "²".isdigit() is True but int("²") raises
        raise UserError(e.t("remove_usage", p=e.cfg.prefix))
    t = e.queue.get(int(a))
    if not t:
        raise UserError(e.t("no_such_item"))
    if not (admin or t.requester.lower() == m.user.lower()):
        raise UserError(e.t("remove_own"))
    if e.queue.remove_track(t):  # by identity: the numbered slot may have shifted since get()
        e.say(e.t("removed", title=t.title))
    else:
        raise UserError(e.t("no_such_item"))


@command("pause", "หยุดชั่วคราว", admin=True)
def _pause(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    e.pause()


@command("resume", "unpause", "เล่นต่อ", admin=True)
def _resume(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    e.resume()


@command("vol", "volume", "เสียง", admin=True)
def _vol(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    if a.isascii() and a.isdigit():
        e.set_volume(int(a[:6]))
    e.say(e.t("volume", v=e.volume))


@command("shuffle", "สุ่ม", admin=True)
def _shuffle(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    if a.lower() not in ("on", "off"):
        raise UserError(e.t("usage_shuffle", p=e.cfg.prefix))
    e.queue.set_shuffle(a.lower() == "on")
    e.say(e.t("shuffle_state", s=e.t(a.lower())))


@command("repeat", "วนซ้ำ", admin=True)
def _repeat(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    if a.lower() not in ("off", "one"):
        raise UserError(e.t("usage_repeat", p=e.cfg.prefix))
    e.queue.repeat = a.lower()
    e.say(e.t("repeat_state", s=e.t(a.lower())))


@command("clear", "ล้างคิว", admin=True)
def _clear(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    e.say(e.t("cleared", n=e.queue.clear()))


@command("clearhistory", "ล้างประวัติ", admin=True)
def _clearhistory(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    n = len(e.history)
    e.history.clear()
    e.say(e.t("history_cleared", n=n))


@command("deletehistory", "delhistory", "ลบประวัติ", admin=True)
def _deletehistory(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    """Delete history entries: !deletehistory all | !deletehistory N (delete last N entries)"""
    if not a:
        raise UserError(e.t("delete_history_usage", p=e.cfg.prefix))
    if a.lower() == "all":
        n = len(e.history)
        e.history.clear()
        e.say(e.t("history_deleted", n=n))
    else:
        try:
            n = int(a)
        except ValueError as err:
            raise UserError(e.t("delete_history_usage", p=e.cfg.prefix)) from err
        if n <= 0:
            raise UserError(e.t("delete_history_usage", p=e.cfg.prefix))

        # Delete last N entries (oldest first, since history is newest first)
        with e.queue.lock:
            to_delete = list(e.history)[-n:]  # oldest N entries
            for t in to_delete:
                try:
                    e.history.remove(t)
                except ValueError:
                    pass
        e.say(e.t("history_deleted", n=min(n, len(to_delete))))


@command("load", "โหลด", admin=True)
def _load(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    if not a:
        raise UserError(e.t("load_usage", p=e.cfg.prefix))
    src = a.strip('"')
    # Reject obviously dangerous paths (absolute system paths outside music dirs)
    if os.path.isabs(src):
        p = Path(src)
        try:
            p = p.resolve()
        except (OSError, ValueError) as err:
            raise UserError(e.t("load_failed", err="invalid path")) from err
        if not any(p.is_relative_to(d) for d in (Path(d).resolve() for d in e.cfg.music_dirs)):
            raise UserError(e.t("folders_admin"))
    e.load_async(src)


@command("say", "พูด", admin=True)
def _say(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    if not a:
        raise UserError(e.t("say_usage", p=e.cfg.prefix))
    e.say(a)


@command("speak", "tts", "ออกเสียง", admin=True)
def _speak(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    if not a:
        raise UserError(e.t("speak_usage", p=e.cfg.prefix))
    e.speak(a)


@command("history", "recent", "ประวัติ")
def _history(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    items = list(e.history)[:5]
    if not items:
        e.say(e.t("history_empty"))
        return
    e.say(
        e.t("history_head") + " " + " | ".join(f"{i}) {_line(t)}" for i, t in enumerate(items, 1))
    )


@command("block", "บล็อก", admin=True)
def _block(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    nick = a.strip()
    if not nick:
        raise UserError(e.t("block_usage", p=e.cfg.prefix))
    if nick.lower() in e.admins:
        raise UserError(e.t("cannot_block_admin"))
    e.blocked.add(nick.lower())
    e.say(e.t("blocked_state", nick=nick))


@command("unblock", "เลิกบล็อก", admin=True)
def _unblock(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    nick = a.strip()
    if not nick:
        raise UserError(e.t("unblock_usage", p=e.cfg.prefix))
    e.blocked.discard(nick.lower())
    e.say(e.t("unblocked_state", nick=nick))


# ---- Mic mute / unmute --------------------------------------------------


@command("mute", "ปิดไมค์", admin=True)
def _mute(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    if not getattr(e.cfg, "admin_mute_mic", False):
        raise UserError(e.t("admin_only"))
    e.mute_mic(True)
    e.say(e.t("mute_on"))


@command("unmute", "เปิดไมค์", admin=True)
def _unmute(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    if not getattr(e.cfg, "admin_unmute_mic", False):
        raise UserError(e.t("admin_only"))
    e.mute_mic(False)
    e.say(e.t("mute_off"))


# ---- Block / unblock bot ------------------------------------------------


@command("blockbot", "บล็อกบอท", admin=True)
def _blockbot(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    nick = a.strip()
    if not nick:
        raise UserError(e.t("block_bot_usage", p=e.cfg.prefix))
    if nick.lower() in e.admins:
        raise UserError(e.t("cannot_block_bot_admin"))
    e.blocked.add(nick.lower())
    e.say(e.t("bot_blocked", nick=nick))


@command("unblockbot", "เลิกบล็อกบอท", admin=True)
def _unblockbot(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    nick = a.strip()
    if not nick:
        raise UserError(e.t("unblock_bot_usage", p=e.cfg.prefix))
    e.blocked.discard(nick.lower())
    e.say(e.t("bot_unblocked", nick=nick))


# ---- Kick / ban / unban user --------------------------------------------


@command("kick", "เตะ", admin=True)
def _kick_user(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    nick = a.strip()
    if not nick:
        raise UserError(e.t("kick_user_usage", p=e.cfg.prefix))
    if nick.lower() in e.admins:
        raise UserError(e.t("cannot_block_admin"))
    e.kick_user(nick)
    e.say(e.t("kicked_user", nick=nick))


@command("ban", "แบน", admin=True)
def _ban_user(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    nick = a.strip()
    if not nick:
        raise UserError(e.t("ban_user_usage", p=e.cfg.prefix))
    if nick.lower() in e.admins:
        raise UserError(e.t("cannot_block_admin"))
    e.ban_user(nick)
    e.say(e.t("banned_user", nick=nick))


@command("unban", "เลิกแบน", admin=True)
def _unban_user(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    nick = a.strip()
    if not nick:
        raise UserError(e.t("unban_user_usage", p=e.cfg.prefix))
    e.unban_user(nick)
    e.say(e.t("unbanned_user", nick=nick))


# ---- Punish user / bot --------------------------------------------------


@command("punish", "ลงโทษ", admin=True)
def _punish_user(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    nick = a.strip()
    if not nick:
        raise UserError(e.t("punish_user_usage", p=e.cfg.prefix))
    if nick.lower() in e.admins:
        raise UserError(e.t("cannot_block_admin"))
    e.punish_user(nick)
    e.say(e.t("punished_user", nick=nick))


@command("punishbot", "ลงโทษบอท", admin=True)
def _punish_bot(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    nick = a.strip()
    if not nick:
        raise UserError(e.t("punish_bot_usage", p=e.cfg.prefix))
    e.punish_bot(nick)
    e.say(e.t("punished_bot", nick=nick))


# ---- Admin delete message ------------------------------------------------


@command("delete", "ลบข้อความ", admin=True)
def _delete_message(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    if not getattr(e.cfg, "admin_delete_message_enabled", False):
        raise UserError(e.t("admin_only"))
    msg_id = a.strip()
    if not msg_id:
        raise UserError(e.t("delete_message_usage", p=e.cfg.prefix))
    ok = e.delete_message(msg_id)
    if ok:
        e.say(e.t("message_deleted"))
    else:
        raise UserError(e.t("cannot_delete_message"))


# ---- Welcome message ------------------------------------------------------


@command("welcome", "ต้อนรับ", admin=True)
def _welcome_message(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    if not a:
        raise UserError(e.t("usage", p=e.cfg.prefix))
    # toggle or set welcome message
    e.set_welcome_message(a.strip())
    e.say(e.t("welcome_enabled") if e.cfg.welcome_message_enabled else e.t("welcome_disabled"))


# ---- Room owner/operator commands -------------------------------------------


@command("owner", "เจ้าของห้อง", admin=True)
def _set_owner(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    """Set room owner via Camfrog command: !owner <nick>"""
    if not a:
        raise UserError(e.t("usage_owner", p=e.cfg.prefix))
    e.say(f"/owner {a.strip()}")


@command("op", "operator", admin=True)
def _set_operator(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    """Set room operator via Camfrog command: !op <nick>"""
    if not a:
        raise UserError(e.t("usage_op", p=e.cfg.prefix))
    e.say(f"/op {a.strip()}")


@command("deop", "เลิกออพ", admin=True)
def _remove_operator(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    """Remove room operator via Camfrog command: !deop <nick>"""
    if not a:
        raise UserError(e.t("usage_deop", p=e.cfg.prefix))
    e.say(f"/deop {a.strip()}")
