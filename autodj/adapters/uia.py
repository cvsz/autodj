from __future__ import annotations

import logging
import os
import re
import threading
import time

from .base import ChatAdapter, ChatMessage, compile_join_rx, diff_lines, parse_join, parse_line

log = logging.getLogger("autodj")


def _read(ctrl) -> str:
    for fn in (
        lambda: ctrl.iface_value.CurrentValue,
        ctrl.window_text,
        lambda: "\n".join(ctrl.texts()),
    ):
        try:
            t = fn()
            if t:
                return t
        except (AttributeError, RuntimeError):
            pass  # try the next read method
    return ""


class UiaAdapter(ChatAdapter):
    """Windows UI Automation. Two layouts:
    - web (Camfrog room window): history/message box are embedded-web panes, see webchat.py
    - text: plain Document/Edit controls chosen by view_type/view_index, input_type/input_index
    view_kind = auto | web | text. `AutoDJ.exe --discover` fills in what it finds."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.rx = re.compile(cfg.line_regex)
        self.join_rx = compile_join_rx(getattr(cfg, "join_line_regex", ""))
        from ..windows import resolve

        c = resolve(
            cfg.window_title_re,
            cfg.window_exclude_re,
            cfg.room,
            cfg.window_index,
            30,
            cfg.process_re,
        )
        if c is None:
            raise RuntimeError(
                f"no visible window matches {cfg.window_title_re!r} "
                f"(open the room window, or run AutoDJ.exe --windows)"
            )
        log.info("attached to window %r (pid %s, class %s)", c.title, c.pid, c.cls)
        self.handle = c.handle
        self.com_lock = (
            threading.RLock()
        )  # UIA/pywinauto is COM-based: readers and senders racing on it break it
        self._view = self._input = None
        self._web = False
        self._bg_fails = 0  # consecutive unconfirmed background sends (auto mode only)
        self._bg_fails_lock = threading.Lock()  # protects _bg_fails across reader/sender threads
        self._attach()

    def _attach(self):
        """(Re)build the window wrapper. A COM failure can wedge the cached wrapper permanently
        (every UIA call keeps failing with 'An event was unable to invoke any of the subscribers' until
        the bot is restarted); dropping it and re-attaching builds fresh COM connections instead.
        """
        from pywinauto import Desktop

        self.win = Desktop(backend="uia").window(handle=self.handle)
        self._view = self._input = None
        self._web = False

    def _find(self, ctype, idx):
        return self.win.descendants(control_type=ctype)[idx]

    def _resolve(self):
        """Locate the chat history (and message box) once; remembered until something fails."""
        if self.win is None:
            self._attach()
        if self.cfg.view_kind in ("auto", "web"):
            from ..webchat import find_web_panes

            view, inp = find_web_panes(self.win, self.cfg.web_view_title, self.cfg.web_input_title)
            if view is not None:
                self._web, self._view, self._input = True, view, inp
                log.info(
                    "chat: web view found (message box %s)",
                    "found" if inp is not None else "MISSING",
                )
                return
            if self.cfg.view_kind == "web":
                raise RuntimeError(f"no pane titled like {self.cfg.web_view_title!r} in the window")
        self._web = False
        self._view = self._find(self.cfg.view_type, self.cfg.view_index)
        self._input = None
        log.info("chat: text control %s[%d]", self.cfg.view_type, self.cfg.view_index)

    def test_connection(self) -> None:
        """Test if the adapter can connect to the Camfrog window.

        Raises:
            RuntimeError: If the window or chat controls cannot be found.
        """
        self._resolve()
        # Verify we can read at least one line
        lines = self._lines()
        if lines:
            log.debug("UIA adapter test_connection: OK (%d lines)", len(lines))
        else:
            log.debug("UIA adapter test_connection: OK (no lines yet)")

    def _lines(self) -> list[str]:
        with self.com_lock:
            if self._view is None:
                self._resolve()
            if self._web:
                from ..webchat import read_web

                return read_web(self._view, strict=self.cfg.web_strict_body)[-300:]
            return _read(self._view).splitlines()[-300:]

    @staticmethod
    def _im_pane_lines(items: list[tuple[str, str]]) -> list[str]:
        """Flat web texts -> 'time|body', skipping date headers."""
        lines: list[str] = []
        pending: str | None = None
        for kind, name in items:
            n = name.strip()
            if not n or kind not in ("text", "link"):
                continue
            if re.match(r"^(วัน|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)", n):
                continue
            if re.fullmatch(r"\d{1,2}:\d{2}(?::\d{2})?", n):
                pending = n
            elif pending is not None:
                lines.append(f"{pending}|{n}")
                pending = None
        return lines

    def _read_im_window(self, w) -> tuple[list[str], str] | None:
        """Return (messages, nick) from one private-chat window, or None."""
        from ..webchat import find_web_panes, read_items

        try:
            from pywinauto import Desktop

            win = Desktop(backend="uia").window(handle=w.handle)
            view, _inp = find_web_panes(win, "wb-log-im-data", "")
            if view is None:
                return None
            nick = w.title.split(" (", 1)[0].strip() or "IM"
            return self._im_pane_lines(read_items(view, tail=400)), nick
        except Exception as ex:  # a chat window can close mid-read
            log.debug("IM pane read failed for %r: %s", w.title, ex)
            return None

    @staticmethod
    def _is_recent(stamp: str, now: float | None = None, window_s: float = 180.0) -> bool:
        """True if an IM line's ``HH:MM[:SS]`` stamp is within *window_s* of now (local time)."""
        try:
            parts = [int(x) for x in stamp.split(":")]
        except ValueError:
            return False
        lt = time.localtime(now)
        msg_s = parts[0] * 3600 + parts[1] * 60 + (parts[2] if len(parts) > 2 else 0)
        now_s = lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec
        age = (now_s - msg_s) % 86400  # wraps across midnight
        return age <= window_s

    def _im_window_messages(self, w, first_scan: bool = False) -> list[ChatMessage]:
        """New messages from one private-chat window.

        Windows open when AutoDJ starts are a baseline (history is never
        replayed).  A window that appears later is a NEW conversation whose
        first message is already in it: the old code baselined that too, so
        the first IM of every chat was silently dropped.  Lines from a new
        window are delivered when their timestamp is recent.
        """
        lock = getattr(self, "com_lock", None)
        if lock is not None:
            with lock:  # UIA is COM-based: never race the sender thread
                got = self._read_im_window(w)
        else:
            got = self._read_im_window(w)
        if got is None:
            self._im_not_im.add(w.handle)  # no IM pane: stop re-scanning this window
            return []
        lines, nick = got
        if not hasattr(self, "_im_handles"):
            self._im_handles: dict[str, int] = {}
        self._im_handles[nick.lower()] = w.handle  # where send_im() answers this user
        prev = self._im_prev.get(w.handle)
        self._im_prev[w.handle] = lines
        if prev is None:
            if first_scan:
                return []  # baseline: never replay old history
            new_lines = [raw for raw in lines if self._is_recent(raw.split("|", 1)[0])]
        else:
            new_lines = diff_lines(prev, lines)
        out: list[ChatMessage] = []
        for raw in new_lines:
            _time, text = raw.split("|", 1)
            if text:
                out.append(ChatMessage(nick, text, is_im=True))
        return out

    def _im_lines(self) -> list[ChatMessage]:
        """Read new private messages from Camfrog IM panes (one per open chat)."""
        out: list[ChatMessage] = []
        first_scan = not hasattr(self, "_im_prev")
        if first_scan:
            self._im_prev: dict[int, list[str]] = {}
        if not hasattr(self, "_im_not_im"):
            self._im_not_im: set[int] = set()  # windows without an IM pane (room list, ...)
        try:
            from ..windows import candidates

            wins = candidates(".*", exe_re=self.cfg.process_re)
        except Exception as ex:
            log.debug("IM window scan failed: %s", ex)
            return out
        own_pid = os.getpid()
        main_handle = getattr(self, "handle", None)
        live: set[int] = set()
        for w in wins:
            # Skip our own windows and the attached room window (``self.pid``
            # was never set, so the old check skipped nothing).
            if w.pid == own_pid or w.handle == main_handle:
                continue
            live.add(w.handle)
            if w.handle in self._im_not_im:
                continue
            out.extend(self._im_window_messages(w, first_scan))
        # Forget closed windows (handles are reused by Windows).
        for gone in [h for h in self._im_prev if h not in live]:
            del self._im_prev[gone]
        self._im_not_im &= live
        return out

    def messages(self):
        prev = None
        while True:
            try:
                lines = self._lines()
            except (OSError, RuntimeError) as e:
                log.debug("chat read failed: %s", e)
                with self.com_lock:  # protect _view/win against reader/sender race
                    self._view = self.win = None  # drop everything: the next poll re-attaches fresh
                time.sleep(1)
                continue
            if prev is not None:
                for line in diff_lines(prev, lines):
                    # Camfrog builds have used several IM markers over time.
                    # Detect all of them; a debug log record makes a new format
                    # easy to spot from the normal startup log.
                    low = line.lower()
                    is_im = (
                        line.startswith(("IM ", "[IM]", "(IM)", "PM ", "Private:", "IM:"))
                        or low.startswith(("im from ", "private message from "))
                        or "[IM]" in line
                        or " (IM) " in line
                    )
                    if is_im:
                        log.info("IM detected: %r", line[:240])
                    m = parse_line(line, self.rx, is_im=is_im)
                    if m is None and not is_im:
                        m = parse_join(line, self.join_rx)  # "<user> has entered the room"
                    if m:
                        yield m
            prev = lines  # first poll only sets the baseline: old history is never replayed
            # Private messages live in a different web pane; read them too.
            try:
                for im in self._im_lines():
                    log.info("IM received: %s: %s", im.user, im.text[:120])
                    yield im
            except Exception:  # IM reading must never break room chat
                log.debug("IM read failed", exc_info=True)
            time.sleep(self.cfg.poll_interval)

    def _ensure_controls(self):
        if self._view is None:
            self._resolve()
        if not self._web and self._input is None:
            self._input = self._find(self.cfg.input_type, self.cfg.input_index)
        if self._input is None:
            raise RuntimeError("chat message box not found")

    def _norm(self, s: str) -> str:
        return " ".join(s.replace("\xa0", " ").split())

    def _appeared(self, text: str, before: list[str]) -> bool:
        """Did `text` show up as a new chat line within a few seconds? (read errors count as 'yes':
        never risk a duplicate post just because the history could not be read)"""
        want = self._norm(text)
        end = time.time() + 5.0  # Extended from 3s to 5s for slower web updates
        while time.time() < end:
            time.sleep(0.5)
            try:
                lines = self._lines()
                new = diff_lines(before, lines) if before else lines
            except (OSError, RuntimeError):
                return True
            for line in new:
                norm_l = self._norm(line)
                # Check multiple match patterns for web chat format variations
                if (
                    norm_l.endswith((": " + want, want))
                    or want in norm_l
                    or (self.cfg.bot_nick and f"{self.cfg.bot_nick}: {want}" in norm_l)
                ):
                    return True
        return False

    def _send_bg(self, text) -> bool:
        from .. import winmsg

        top = int(self.win.handle)
        winmsg.show_noactivate(top)

        # Try multiple strategies in order of reliability for Chromium-based web editors
        # _ensure_controls() guarantees self._input is not None here
        if self._input is None:  # explicit check: asserts are stripped under python -O
            raise RuntimeError("_ensure_controls must be called before _send_bg")
        r = self._input.rectangle()
        pt = ((r.left + r.right) // 2, (r.top + r.bottom) // 2)

        # Strategy 1: WM_SETTEXT (most reliable for Chromium contenteditable)
        # This sets the entire text at once via SendMessage
        try:
            if winmsg.post_text_rich(top, pt, text, enter=True, click=True):
                log.debug("sent via WM_SETTEXT (rich)")
                return True
        except (OSError, RuntimeError) as e:
            log.debug("WM_SETTEXT failed: %s", e)

        # Strategy 2: UIA ValuePattern SetValue
        try:
            if self._input is None:
                raise RuntimeError("chat input control is not available")
            vp = self._input.iface_value
            if self._input.iface.CurrentIsEnabled and not vp.CurrentIsReadOnly:
                vp.SetValue(text)
                # Send Enter via posted message
                if winmsg.post_text(top, pt, "", enter=True, click=False):
                    log.debug("sent via UIA SetValue + Enter")
                    return True
        except (OSError, RuntimeError, AttributeError) as e:
            log.debug("UIA SetValue failed: %s", e)

        # Strategy 3: Posted WM_CHAR with IME composition (fallback)
        try:
            if winmsg.post_text(top, pt, text, enter=True, click=True):
                log.debug("sent via posted WM_CHAR")
                return True
        except (OSError, RuntimeError) as e:
            log.debug("posted WM_CHAR failed: %s", e)

        return False

    def _send_fg(self, text):
        import pyperclip
        from pywinauto.keyboard import send_keys

        from .. import winmsg

        prev = winmsg.foreground()
        try:
            old_clip = pyperclip.paste()
        except (pyperclip.PyperclipException, OSError):
            old_clip = None
        try:
            try:
                if self.win.is_minimized():
                    self.win.restore()
            except (RuntimeError, AttributeError):
                pass  # window may have closed; proceed with foreground send
            self.win.set_focus()  # keystrokes go to the foreground window, so bring Camfrog up first
            # _ensure_controls() guarantees self._input is not None here
            if self._input is None:  # explicit check: asserts are stripped under python -O
                raise RuntimeError("_ensure_controls must be called before _send_fg")
            if self._web:
                self._input.click_input()  # the message box is a web editor: only a click focuses it
            else:
                self._input.set_focus()
            pyperclip.copy(text)  # clipboard paste keeps Thai/Unicode intact
            send_keys("^v")
            time.sleep(0.15)
            send_keys("{ENTER}")
        finally:
            time.sleep(0.1)
            if old_clip is not None:
                try:
                    pyperclip.copy(old_clip)
                except (pyperclip.PyperclipException, OSError):
                    pass  # clipboard restore is best-effort
            if prev and prev != int(self.win.handle):
                winmsg.restore_foreground(prev)  # give the user their window back

    def send_im(self, user: str, text: str) -> None:
        """Answer *user* privately in their open Camfrog IM window.

        Background send first (posted messages, no focus change), verified by
        reading the IM history back; if the line does not show up, falls back to
        focus + paste + Enter and gives the user their foreground window back.
        Raises RuntimeError when there is no IM window for *user*.
        """
        from pywinauto import Desktop

        from .. import winmsg
        from ..webchat import find_web_panes, read_items

        with self.com_lock:
            handle = getattr(self, "_im_handles", {}).get(user.lower())
            if handle is None:
                raise RuntimeError(f"no open IM window for {user!r}")
            win = Desktop(backend="uia").window(handle=handle)
            view, inp = find_web_panes(win, "wb-log-im-data", self.cfg.web_input_title)
            if view is None or inp is None:
                raise RuntimeError(f"IM window for {user!r} has no message box")

            def shown() -> int:
                lines = self._im_pane_lines(read_items(view, tail=60))
                return sum(1 for ln in lines if ln.split("|", 1)[-1].strip() == text.strip())

            before = shown()
            winmsg.show_noactivate(handle)
            r = inp.rectangle()
            pt = ((r.left + r.right) // 2, (r.top + r.bottom) // 2)
            try:
                winmsg.post_text_rich(handle, pt, text, enter=True, click=True)
            except (OSError, RuntimeError) as e:
                log.debug("IM background send failed: %s", e)
            for _ in range(20):  # up to 4 s: a slow render must not trigger a 2nd send
                time.sleep(0.2)
                if shown() > before:
                    log.debug("IM sent to %s (background)", user)
                    return
            self._send_im_fg(win, inp, text)
            log.debug("IM sent to %s (foreground)", user)

    @staticmethod
    def _send_im_fg(win, inp, text: str) -> None:
        import pyperclip
        from pywinauto.keyboard import send_keys

        from .. import winmsg

        prev = winmsg.foreground()
        try:
            old_clip = pyperclip.paste()
        except (pyperclip.PyperclipException, OSError):
            old_clip = None
        try:
            try:
                if win.is_minimized():
                    win.restore()
            except (RuntimeError, AttributeError):
                pass
            win.set_focus()
            inp.click_input()  # web editor: only a click focuses it
            pyperclip.copy(text)  # clipboard paste keeps Thai/Unicode intact
            send_keys("^a")  # replace anything a failed background send left in the box
            send_keys("^v")
            time.sleep(0.15)
            send_keys("{ENTER}")
        finally:
            time.sleep(0.1)
            if old_clip is not None:
                try:
                    pyperclip.copy(old_clip)
                except (pyperclip.PyperclipException, OSError):
                    pass
            if prev and prev != int(win.handle):
                winmsg.restore_foreground(prev)

    def send(self, text):
        """Serialized entry point. UIA is COM-based: the reader thread and the sender thread must never
        touch the same wrappers at once (a racing call wedges COM with 'An event was unable to invoke
        any of the subscribers' until the process is restarted)."""
        with self.com_lock:
            try:
                self._do_send(text)
            except (OSError, RuntimeError):
                self.win = self._view = self._input = (
                    None  # re-attach + re-resolve everything next time
                )
                raise

    def _do_send(self, text):
        """send_mode: background (posted messages, no focus change) | foreground (focus + paste) |
        auto (background, then check the line appeared in the room; if not, foreground).
        """
        mode = self.cfg.send_mode
        try:
            self._ensure_controls()
            if mode in ("auto", "background"):
                decision = self._attempt_background_send(text, mode)
                if decision == "sent":
                    return
                if mode == "background":
                    # background never falls back to foreground
                    if decision == "failed":
                        raise RuntimeError(
                            "background send failed (try send_mode = 'auto' or 'foreground')"
                        )
                    return
                # mode == "auto" and background did not confirm: fall through to foreground
            self._send_fg(text)
            if self.cfg.send_verify and not self._appeared(text, []):
                log.warning(
                    "sent via foreground paste but NOT seen in the room within 3s "
                    "(the message box may not have received the paste/enter)"
                )
            log.debug("sent to Camfrog: %s", text)
        except Exception:
            self._view = self._input = None  # re-resolve the controls next time
            raise

    def _attempt_background_send(self, text, mode):
        """Try sending in the background up to twice.

        Returns "sent" (confirmed or background-only), "fallback" (auto mode should try foreground),
        or "failed" (background mode could not send at all).
        """
        allow_bg = self._bg_allowed(mode)
        if not allow_bg:
            return "fallback"
        before = self._bg_before(text, mode)
        ok = False
        # Try up to 2 times with different strategies
        for attempt in range(2):
            if self._bg_one_attempt(text, before, mode, attempt + 1):
                ok = True
                return "sent"
            time.sleep(0.5)
        return self._bg_after_loop(text, ok, before, mode)

    def _bg_allowed(self, mode: str) -> bool:
        # after 2 unconfirmed background sends in a row, go straight to the foreground for a
        # while: announcements must not stack seconds of verify+fallback latency every track
        if mode == "background":
            return True
        with self._bg_fails_lock:
            return self._bg_fails < 2

    def _bg_before(self, text, mode):
        before = None
        if mode == "auto" and self.cfg.send_verify:
            try:
                before = self._lines()
            except (OSError, RuntimeError):
                before = None
        return before

    def _bg_one_attempt(self, text, before, mode, attempt: int) -> bool:
        """One background send attempt (+ verify when auto). Returns True when done."""
        try:
            ok = self._send_bg(text)
        except (OSError, RuntimeError) as e:
            log.warning("background send attempt %d failed: %s", attempt, e)
            return False
        if not ok:
            return False
        if mode == "auto" and self.cfg.send_verify:
            # Verify the message appeared
            if before is None or self._appeared(text, before):
                log.debug("sent in background (attempt %d): %s", attempt, text)
                with self._bg_fails_lock:
                    self._bg_fails = 0
                return True
            log.warning("background send not confirmed in the room (attempt %d)", attempt)
            return False
        log.debug("sent in background (attempt %d): %s", attempt, text)
        with self._bg_fails_lock:
            self._bg_fails = 0
        return True

    def _bg_after_loop(self, text: str, ok: bool, before, mode: str) -> str:
        """Decide what to do after the background retry loop exhausted its attempts."""
        with self._bg_fails_lock:
            self._bg_fails += 1
            bg_fails = self._bg_fails
        log.info(
            "background send not confirmed in the room (%d in a row): falling back to foreground",
            bg_fails,
        )
        if mode == "background":
            if not ok:
                return "failed"
            return "sent"
        if ok and (not self.cfg.send_verify or before is None or self._appeared(text, before)):
            log.debug("sent in background: %s", text)
            with self._bg_fails_lock:
                self._bg_fails = 0
            return "sent"
        with self._bg_fails_lock:
            self._bg_fails += 1
            bg_fails = self._bg_fails
        log.info(
            "background send not confirmed in the room (%d in a row): falling back to foreground",
            bg_fails,
        )
        return "fallback"
