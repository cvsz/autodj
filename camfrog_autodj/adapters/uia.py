from __future__ import annotations

import logging
import re
import threading
import time

from .base import ChatAdapter, diff_lines, parse_line

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
        the bot is restarted); dropping it and re-attaching builds fresh COM connections instead."""
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
                    # IM (private) messages in Camfrog are marked with an [IM] tag or "IM " prefix
                    is_im = line.startswith(("IM ", "[IM]")) or " [IM] " in line
                    m = parse_line(line, self.rx, is_im=is_im)
                    if m:
                        yield m
            prev = lines  # first poll only sets the baseline: old history is never replayed
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
        assert self._input is not None, "_ensure_controls must be called before _send_bg"
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
            assert self._input is not None
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
            assert self._input is not None, "_ensure_controls must be called before _send_fg"
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
        auto (background, then check the line appeared in the room; if not, foreground)."""
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
        # Increment failure counter exactly once per call (avoid double-counting)
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
        return "fallback"
