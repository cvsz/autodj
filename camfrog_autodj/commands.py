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

from .exceptions import UserError

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
        e = self.e
        p = e.cfg.prefix
        # Fail-closed: empty prefix means no commands are recognized;
        # also protects against console auth bypass where every line has no prefix.
        if not p.strip():
            return
        text = msg.text.strip()
        is_im = getattr(msg, "is_im", False)
        parsed = self._parse_command(text, p, is_im)
        if parsed is None:
            return
        name, arg = parsed
        entry = COMMANDS.get(name.lower())
        admin = self.is_admin(msg)
        if is_im:
            log.info(
                "im command %s (%s) from %s%s",
                name,
                arg,
                msg.user,
                ", admin" if admin else "",
            )
        else:
            log.info(
                "command %s%s (%s) from %s%s",
                p,
                name,
                arg,
                msg.user,
                ", admin" if admin else "",
            )
        if not entry:
            return
        fn, need_admin = entry
        if not admin and msg.user.lower() in e.blocked:
            log.info(
                "blocked: ignoring %s's command from %s",
                msg.user,
                "IM" if is_im else "room",
            )
            return  # blocked users get no reply at all
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
        """
        e = self.e
        who = (
            msg.user.lower()
        )  # "Bob" and "bob" are one person: changing case must not dodge the cooldown
        if now - self.last.get(who, -1e9) < e.cfg.cooldown:
            log.info(
                "cooldown: dropping %s's command from %s (%.1fs to go)",
                msg.user,
                "IM" if is_im else "room",
                e.cfg.cooldown - (now - self.last[who]),
            )
            return False
        # Sliding window request limit per user
        if name.lower() in ("play", "request", "req", "p", "เล่น"):
            limit = getattr(e.cfg, "user_request_limit", 5)
            window = getattr(e.cfg, "rate_limit_window", 300.0)
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


def _cut_current(e: "Engine") -> None:
    """Stop the current track so the next queued request plays immediately.

    Used by ``!play`` so a new request cuts in now instead of making the user
    wait for the current track to finish. Safe to call when nothing is playing.
    """
    if e.current:
        e.skip()


@command("help", "commands", "ช่วยเหลือ")
def _help(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    p = e.cfg.prefix
    e.say(e.t("help_base", p=p) + (e.t("help_admin", p=p) if admin else ""))


@command("hadj", "คู่มือคำสั่ง", "คู่มือ")
def _hadj(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    """Send the full IM help guide (both pages) to the user.

    Works via IM (no prefix) or in the room (with prefix). Replies are posted
    to the room via ``e.say()``, matching the existing command-reply pattern.
    """
    full = (
        e.t(
            "help_im_page1",
            BOT=e.cfg.bot_nick,
            ROOM=e.cfg.room,
        )
        + "\n"
        + e.t("help_im_page2")
        + "\n"
        + e.t("help_im_next_page")
    )
    e.say(full)


@command("skipp", "ข้ามเพลง", admin=True)
def _skipp(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    """ข้ามเพลงปัจจุบัน — ผู้ขอหรือ Main Owner เท่านั้น (alias ของ /skip)."""
    _skip(e, m, a, admin)


@command("nowp")
def _nowp(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    """ดูเพลงปัจจุบันและผู้ขอ (alias ของ /np)."""
    _np(e, m, a, admin)


@command("lastp")
def _lastp(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    """ดูเพลงที่เล่นไปล่าสุด (alias ของ /last)."""
    _last(e, m, a, admin)


@command("aplay", "addm")
def _aplay(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    """ขอเพลงผ่าน IM (alias ของ /play) รองรับการมอบเพลงด้วย @{USER} เช่น /aplay ครับพี่ @user"""
    stripped = a.strip()
    if stripped.lower().startswith("fav "):
        _aplay_fav(e, m, stripped, admin)
        return
    _play(e, m, a, admin)


def _aplay_fav(e: "Engine", m: "ChatMessage", stripped: str, admin: bool) -> None:
    """เล่นเพลงโปรดจากคำสั่ง /aplay fav <ลำดับ>."""
    try:
        index = int(stripped[4:].strip())
    except ValueError as err:
        raise UserError(e.t("aplay_fav_usage", p=e.cfg.prefix)) from err
    from .favorites import FavoritesStore

    fav = FavoritesStore(e.cfg_path)
    entry = fav.get(m.user, index)
    if not entry:
        raise UserError(e.t("aplay_fav_not_found", n=index))
    # เล่นเพลงโปรดโดยตรง
    tracks = e.resolve(entry["source"], m.user, admin)
    if not tracks:
        raise UserError(e.t("nothing_found"))
    if not admin:
        _assert_queue_capacity(e, m.user)  # Fast pre-check
        for t in tracks:
            _assert_not_already_queued(e, t)  # Prevent duplicate favorite requests
    pos = 0
    with e.queue.lock:  # Re-check under lock to prevent TOCTOU race
        if not admin:
            _assert_queue_capacity(e, m.user)
            _assert_not_already_queued(e, tracks[0])
        for t in tracks:
            pos = e.queue.add_request(t, position=0)
            e.record_request(t.source, t.title)
    e.wake.set()
    _cut_current(e)
    e._last_user_request_time = time.monotonic()
    if e._autoplay_mode:
        e._autoplay_mode = False
        log.info("Autoplay mode deactivated: new user request received")
    if len(tracks) == 1:
        e.say(
            e.t(
                "queued_one",
                pos=pos,
                title=tracks[0].title,
                dur=tracks[0].dur,
                user=m.user,
            )
        )
    else:
        e.say(e.t("queued_many", n=len(tracks), user=m.user))


@command("play", "request", "req", "p", "เล่น", "ขอเพลง", "เล่นเพลง", "เปิดเพลง")
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
            e.record_request(t.source, t.title)  # บันทึกสถิติสำหรับ /topm
    e.wake.set()
    _cut_current(e)
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
    passed, msg = e.voteskip(m.user)
    e.say(msg)


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
    if not getattr(e.cfg, "admin_block_user", False):
        raise UserError(e.t("admin_only"))
    nick = a.strip()
    if not nick:
        raise UserError(e.t("block_usage", p=e.cfg.prefix))
    if nick.lower() in e.admins:
        raise UserError(e.t("cannot_block_admin"))
    e.blocked.add(nick.lower())
    e.say(e.t("blocked_state", nick=nick))


@command("unblock", "เลิกบล็อก", admin=True)
def _unblock(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    if not getattr(e.cfg, "admin_unblock_user", False):
        raise UserError(e.t("admin_only"))
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
    if not getattr(e.cfg, "admin_block_bot", False):
        raise UserError(e.t("admin_only"))
    nick = a.strip()
    if not nick:
        raise UserError(e.t("block_bot_usage", p=e.cfg.prefix))
    if nick.lower() == e.cfg.bot_nick.lower():
        raise UserError(e.t("cannot_block_bot_admin"))
    if nick.lower() in e.admins:
        raise UserError(e.t("cannot_block_admin"))
    e.blocked.add(nick.lower())
    e.say(e.t("bot_blocked", nick=nick))


@command("unblockbot", "เลิกบล็อกบอท", admin=True)
def _unblockbot(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    if not getattr(e.cfg, "admin_unblock_bot", False):
        raise UserError(e.t("admin_only"))
    nick = a.strip()
    if not nick:
        raise UserError(e.t("unblock_bot_usage", p=e.cfg.prefix))
    e.blocked.discard(nick.lower())
    e.say(e.t("bot_unblocked", nick=nick))


# ---- Kick / ban / unban user --------------------------------------------


@command("kick", "เตะ", admin=True)
def _kick_user(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    if not getattr(e.cfg, "admin_kick_user", False):
        raise UserError(e.t("admin_only"))
    nick = a.strip()
    if not nick:
        raise UserError(e.t("kick_user_usage", p=e.cfg.prefix))
    if nick.lower() in e.admins:
        raise UserError(e.t("cannot_block_admin"))
    e.kick_user(nick)
    e.say(e.t("kicked_user", nick=nick))


@command("ban", "แบน", admin=True)
def _ban_user(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    if not getattr(e.cfg, "admin_ban_user", False):
        raise UserError(e.t("admin_only"))
    nick = a.strip()
    if not nick:
        raise UserError(e.t("ban_user_usage", p=e.cfg.prefix))
    if nick.lower() in e.admins:
        raise UserError(e.t("cannot_block_admin"))
    e.ban_user(nick)
    e.say(e.t("banned_user", nick=nick))


@command("unban", "เลิกแบน", admin=True)
def _unban_user(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    if not getattr(e.cfg, "admin_unban_user", False):
        raise UserError(e.t("admin_only"))
    nick = a.strip()
    if not nick:
        raise UserError(e.t("unban_user_usage", p=e.cfg.prefix))
    e.unban_user(nick)
    e.say(e.t("unbanned_user", nick=nick))


# ---- Punish user / bot --------------------------------------------------


@command("punish", "ลงโทษ", admin=True)
def _punish_user(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    if not getattr(e.cfg, "admin_punish_user", False):
        raise UserError(e.t("admin_only"))
    nick = a.strip()
    if not nick:
        raise UserError(e.t("punish_user_usage", p=e.cfg.prefix))
    if nick.lower() in e.admins:
        raise UserError(e.t("cannot_block_admin"))
    e.punish_user(nick)
    e.say(e.t("punished_user", nick=nick))


@command("punishbot", "ลงโทษบอท", admin=True)
def _punish_bot(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    if not getattr(e.cfg, "admin_punish_bot", False):
        raise UserError(e.t("admin_only"))
    nick = a.strip()
    if not nick:
        raise UserError(e.t("punish_bot_usage", p=e.cfg.prefix))
    if nick.lower() == e.cfg.bot_nick.lower():
        raise UserError(e.t("cannot_block_bot_admin"))
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


# ============================================================================
# ขอเพลงและดูคิว / Song requests (IM commands) — ตามคู่มือ /hadj
# ============================================================================


@command("hbdp", "hbdm", "อวยพรวันเกิด", admin=False)
def _hbdp(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    """อวยพรวันเกิดหน้าห้อง + เปิดเพลงวันเกิด"""
    if not a:
        raise UserError(e.t("hbdp_usage", p=e.cfg.prefix))
    name = a.strip()
    # อวยพรวันเกิดในห้อง
    e.say(e.t("hbdp_wish", name=name))
    # เปิดเพลงวันเกิด (ใช้ resolve ค้นหาเพลงวันเกิด)
    tracks = e.resolve("生日快乐 happy birthday", "AutoDJ", True)
    if not tracks:
        # fallback: ค้นหาเป็นภาษาอังกฤษ
        tracks = e.resolve("happy birthday", "AutoDJ", True)
    if tracks:
        with e.queue.lock:
            for t in tracks:
                e.queue.add_request(t, position=0)
        e.wake.set()
        _cut_current(e)
        e.say(e.t("hbdp_playing", title=tracks[0].title, name=name))
    else:
        e.say(e.t("hbdp_no_song", name=name))


@command("topp", "topm", "เพลงขอสูงสุด", admin=False)
def _topp(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    """เพลงที่ถูกขอมากสุดวันนี้ (/topm week = สัปดาห์นี้)"""
    period = a.strip().lower() if a else "today"
    if period not in ("today", "week"):
        period = "today"
    top = e.top_requests(period=period, limit=5)
    if not top:
        e.say(e.t("topp_none", period=period))
        return
    lines = " | ".join(f"{i + 1}) {t['title']} ({t['count']} ครั้ง)" for i, t in enumerate(top))
    e.say(e.t("topp_list", period=period, list=lines))


@command("favp", "favm", "เพลงโปรด", admin=False)
def _favp(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    """เก็บเพลงที่กำลังเล่นไว้ในเพลงโปรด"""
    cur = e.current
    if not cur:
        raise UserError(e.t("nothing_playing"))
    from .favorites import FavoritesStore

    fav = FavoritesStore(e.cfg_path)
    fav.add(m.user, cur)
    e.say(e.t("favp_saved", title=cur.title))


@command("myfavp", "myfavm", "ดูเพลงโปรด", admin=False)
def _myfavp(e: "Engine", m: "ChatMessage", a: str, admin: bool) -> None:
    """ดูเพลงโปรดของตัวเอง"""
    from .favorites import FavoritesStore

    fav = FavoritesStore(e.cfg_path)
    items = fav.list_for(m.user)
    if not items:
        e.say(e.t("myfavp_empty"))
        return
    lines = " | ".join(f"{i + 1}) {it['title']}" for i, it in enumerate(items[:10]))
    e.say(e.t("myfavp_list", list=lines))
