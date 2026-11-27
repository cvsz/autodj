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


# Room message box (WebView2): time for the editor to take the focus after the click,
# and for the pasted text to land before Enter.
_WEB_FOCUS_DELAY = 0.5
_WEB_PASTE_DELAY = 0.3


class RoomHiddenError(RuntimeError):
    """Camfrog's window shows another page (the room list, another tab): there is
    no room chat to read or type into until the room tab is selected again."""


def _window_title(handle: int) -> str:
    import ctypes

    buf = ctypes.create_unicode_buffer(512)
    ctypes.windll.user32.GetWindowTextW(handle, buf, 512)  # type: ignore[attr-defined]
    return buf.value


# Foreground sends take the keyboard focus.  Live 2026-11-23 the operator was
# typing on the bot PC ("ตรวจ ภาษา") while the bot pasted: their keystrokes went
# into the Camfrog message box and were posted glued to the bot's lines
# ("วเข้าคิวที่ 1 ...").  So a foreground send first waits until nobody has used
# the keyboard or mouse for a moment, and types nothing if the PC stays busy.
_IDLE_REQUIRED_S = 2.5
_IDLE_MAX_WAIT_S = 30.0


def _idle_seconds() -> float:
    """Seconds since the last keyboard/mouse input on this desktop (inf if unknown)."""
    import ctypes
    from ctypes import wintypes

    class _LastInputInfo(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

    try:
        info = _LastInputInfo()
        info.cbSize = ctypes.sizeof(info)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):  # type: ignore[attr-defined]
            return float("inf")
        now = ctypes.windll.kernel32.GetTickCount() & 0xFFFFFFFF  # type: ignore[attr-defined]
    except (AttributeError, OSError):  # not Windows / API unavailable: never block sends
        return float("inf")
    return ((now - info.dwTime) & 0xFFFFFFFF) / 1000.0


def _wait_user_idle(what: str) -> None:
    """Wait until the user has been idle for _IDLE_REQUIRED_S; RuntimeError after
    _IDLE_MAX_WAIT_S of continuous activity (nothing is typed)."""
    deadline = time.monotonic() + _IDLE_MAX_WAIT_S
    waited = False
    while True:
        idle = _idle_seconds()
        if idle >= _IDLE_REQUIRED_S:
            if waited:
                log.info("%s: waited for the user to stop typing", what)
            return
        if time.monotonic() >= deadline:
            raise RuntimeError(
                f"{what}: someone is using the keyboard/mouse on this PC; nothing typed"
            )
        waited = True
        time.sleep(min(0.5, _IDLE_REQUIRED_S - idle + 0.05))


def _press_ctrl_v() -> None:
    """Press Ctrl+V by virtual-key code, whatever the keyboard layout.

    pywinauto's ``send_keys("^v")`` looks the 'v' up with VkKeyScanW() in the
    *current* layout.  With the Thai layout active there is no 'v' (-1), so
    only Ctrl was pressed and nothing was pasted, while the following Enter
    still went through: live 2026-11-22 every room send was empty, and a draft
    left in the message box was posted instead of the bot's text.
    """
    import ctypes

    u32 = ctypes.windll.user32  # type: ignore[attr-defined]
    vk_control, vk_v, keyup = 0x11, 0x56, 0x0002
    u32.keybd_event(vk_control, 0, 0, 0)
    u32.keybd_event(vk_v, 0, 0, 0)
    u32.keybd_event(vk_v, 0, keyup, 0)
    u32.keybd_event(vk_control, 0, keyup, 0)


def _bring_to_front(u32, handle: int) -> None:
    """BringWindowToTop + SetForegroundWindow while attached to the input queue of
    the current foreground window.

    Windows refuses SetForegroundWindow from a background process for the
    foreground lock time-out (200 s by default) after the user's last input: live
    2026-11-23 every send failed with "could not be brought to the front" while
    the operator worked in a terminal.  Attaching to the foreground thread's input
    queue for the call is the documented way around the lock; no key is pressed.
    """
    import threading

    fg = u32.GetForegroundWindow()
    fg_thread = u32.GetWindowThreadProcessId(fg, None) if fg and fg != handle else 0
    me = threading.get_native_id()
    attached = (
        bool(fg_thread) and fg_thread != me and bool(u32.AttachThreadInput(me, fg_thread, True))
    )
    try:
        u32.BringWindowToTop(handle)
        u32.SetForegroundWindow(handle)
    finally:
        if attached:
            u32.AttachThreadInput(me, fg_thread, False)


def _foreground_is_elevated(u32) -> bool:
    """True when the foreground window belongs to a process running as administrator
    while we do not: Windows (UIPI) never lets a normal process take the focus
    from it, whatever the code does.  False when unknown."""
    import ctypes
    from ctypes import wintypes

    try:
        # private DLL objects: typed handles here must not change ctypes.windll users
        adv = ctypes.WinDLL("advapi32")  # type: ignore[attr-defined]
        k32 = ctypes.WinDLL("kernel32")  # type: ignore[attr-defined]
    except (AttributeError, OSError):  # not Windows
        return False
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    adv.OpenProcessToken.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    adv.GetTokenInformation.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    adv.GetSidSubAuthorityCount.restype = ctypes.POINTER(ctypes.c_ubyte)
    adv.GetSidSubAuthorityCount.argtypes = [ctypes.c_void_p]
    adv.GetSidSubAuthority.restype = ctypes.POINTER(wintypes.DWORD)
    adv.GetSidSubAuthority.argtypes = [ctypes.c_void_p, wintypes.DWORD]

    def level(proc) -> int:
        tok = wintypes.HANDLE()
        if not adv.OpenProcessToken(proc, 0x0008, ctypes.byref(tok)):  # TOKEN_QUERY
            return -1
        try:
            need = wintypes.DWORD()
            adv.GetTokenInformation(tok, 25, None, 0, ctypes.byref(need))  # TokenIntegrityLevel
            buf = ctypes.create_string_buffer(need.value or 64)
            if not adv.GetTokenInformation(tok, 25, buf, len(buf), ctypes.byref(need)):
                return -1
            sid = ctypes.cast(buf, ctypes.POINTER(ctypes.c_void_p))[0]
            count = adv.GetSidSubAuthorityCount(sid)[0]
            return int(adv.GetSidSubAuthority(sid, count - 1)[0])
        finally:
            k32.CloseHandle(tok)

    try:
        pid = wintypes.DWORD()
        u32.GetWindowThreadProcessId(u32.GetForegroundWindow(), ctypes.byref(pid))
        if not pid.value:
            return False
        other = k32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not other:
            return False
        try:
            theirs = level(other)
        finally:
            k32.CloseHandle(other)
        ours = level(k32.GetCurrentProcess())
        return ours >= 0 and theirs > ours
    except (AttributeError, OSError, ValueError, ctypes.ArgumentError):
        return False


def _focus_target(handle: int, x: int, y: int, what: str) -> None:
    """Make *handle* the foreground window and check that (x, y) belongs to it.

    Keystrokes go to whatever window has the focus.  Without these checks a
    send that could not take the focus (Windows refuses focus changes while the
    user works in another app) clicked and pasted + Enter into that other app:
    live 2026-11-22, no announcement reached the room for ~1.5 h while a
    terminal was the foreground window.  Raises RuntimeError and types nothing
    when the window cannot be brought to the front or is covered.
    """
    import ctypes
    from ctypes import wintypes

    u32 = ctypes.windll.user32  # type: ignore[attr-defined]
    if u32.IsIconic(handle):
        u32.ShowWindow(handle, 9)  # SW_RESTORE
    deadline = time.monotonic() + 2.0
    while u32.GetForegroundWindow() != handle and time.monotonic() < deadline:
        _bring_to_front(u32, handle)
        time.sleep(0.1)
    if u32.GetForegroundWindow() != handle:
        if _foreground_is_elevated(u32):
            # live 2026-11-23: an administrator Windows Terminal was in front
            raise RuntimeError(
                f"{what} could not be brought to the front: the window in front belongs "
                "to a program running as administrator (Windows does not let AutoDJ take "
                "the focus from it; minimize or close that window); nothing typed"
            )
        raise RuntimeError(f"{what} could not be brought to the front; nothing typed")
    hit = u32.WindowFromPoint(wintypes.POINT(x, y))
    if not hit or u32.GetAncestor(hit, 2) != handle:  # GA_ROOT
        raise RuntimeError(f"{what} message box is covered by another window; nothing typed")


def _still_front(handle: int, what: str) -> None:
    """Abort before a keystroke if another window took the focus meanwhile."""
    import ctypes

    if ctypes.windll.user32.GetForegroundWindow() != handle:  # type: ignore[attr-defined]
        raise RuntimeError(f"{what} lost the focus before typing; nothing typed")


def _keys_literal(text: str) -> str:
    """*text* as literal keystrokes for pywinauto.send_keys (newlines become spaces)."""
    text = text.replace("\r", " ").replace("\n", " ")
    return "".join("{%s}" % c if c in "+^%~(){}[]" else c for c in text)


_IM_PREFIXES = ("IM ", "[IM]", "(IM)", "PM ", "Private:", "IM:")
_IM_PREFIXES_LOWER = ("im from ", "private message from ")
_STAMP_RE = re.compile(r"^\s*\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*")
_IM_HEADER_MARK_RE = re.compile(r"(?:^|\s)(?:\[IM\]|\(IM\))(?:\s|$)")


def _has_im_marker(line: str) -> bool:
    """True when a room-history line is marked as an instant message.

    The marker counts only in the line's *header* -- the optional ``H:MM``
    stamp plus the nick, i.e. everything before the first ``": "``.  The
    message body never counts: the bot's own room reply "... (IM) ..." used to
    come back as an IM from the bot's own account, which then tried to answer
    itself ("no open IM window for 'Seaza'") on every read.
    """
    rest = _STAMP_RE.sub("", line, count=1)
    for s in (line, rest):
        if s.startswith(_IM_PREFIXES) or s.lower().startswith(_IM_PREFIXES_LOWER):
            return True
    header = rest.split(": ", 1)[0] if ": " in rest else ""
    return bool(_IM_HEADER_MARK_RE.search(header))


class UiaAdapter(ChatAdapter):
    """Windows UI Automation. Two layouts:
    - web (Camfrog room window): history/message box are embedded-web panes, see webchat.py
    - text: plain Document/Edit controls chosen by view_type/view_index, input_type/input_index
    view_kind = auto | web | text. `AutoDJ.exe --discover` fills in what it finds."""

    # Web room chat: the window title seen when the chat panes were found.  Camfrog
    # shows the room list (or another tab) in the same window; the cached panes
    # then still answer with the old room's text and position, so a changed title
    # means "look the panes up again" (see _check_room_shown).  Class-level
    # defaults so subclasses and test doubles that skip __init__ keep working.
    _web_room: bool = False
    _room_title: str | None = None
    _room_hidden: bool = False
    _hidden_title: str | None = None
    _hidden_checked: float = 0.0
    # Background sends paused after 2 unconfirmed ones are tried again after this.
    BG_RETRY_S = 1800.0
    _bg_retry_at: float = 0.0
    # A private message in the room pane older than this (by its stamp) is history.
    IM_MAX_AGE_S = 300.0
    # Room page hidden this long (and the PC idle) -> select the room tab again.
    ROOM_TAB_RESELECT_S = 45.0
    ROOM_TAB_IDLE_S = 30.0
    _hidden_since: float = 0.0
    _tab_tried_at: float = float("-inf")
    # Seconds before a Camfrog window without an IM pane is looked at again.
    IM_PANE_RECHECK_S = 10.0

    @property
    def room_ready(self) -> bool:
        """False while Camfrog shows another page (room list, tab) instead of the room."""
        return not self._room_hidden

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
        self._web_room = False
        self._room_title = None
        self._room_hidden = False
        self._hidden_title = None
        self._hidden_checked = 0.0
        self._attach()

    # Keys that choose the window: changing them needs a new attach (restart).
    _ATTACH_KEYS = ("window_title_re", "window_exclude_re", "room", "window_index", "process_re")

    def apply_config(self, cfg) -> None:
        """Take a hot-reloaded config: patterns, poll interval, send mode, pane titles.

        The chat panes are looked up again with the new titles on the next read.
        """
        old = self.cfg
        rx = re.compile(cfg.line_regex)  # validated at load; compile before swapping
        join_rx = compile_join_rx(getattr(cfg, "join_line_regex", ""))
        with self.com_lock:
            self.cfg, self.rx, self.join_rx = cfg, rx, join_rx
            self._view = self._input = None
        changed = [k for k in self._ATTACH_KEYS if getattr(old, k, None) != getattr(cfg, k, None)]
        if changed:
            log.info(
                "chat window settings changed (%s): used from the next start", ", ".join(changed)
            )

    def _attach(self):
        """(Re)build the window wrapper. A COM failure can wedge the cached wrapper permanently
        (every UIA call keeps failing with 'An event was unable to invoke any of the subscribers' until
        the bot is restarted); dropping it and re-attaching builds fresh COM connections instead.
        """
        from pywinauto import Desktop

        self.win = Desktop(backend="uia").window(handle=self.handle)
        self._view = self._input = None
        self._web = False

    def _room_line_message(self, line: str) -> ChatMessage | None:
        """A new room-history line as a ChatMessage (chat line, IM line or join notice)."""
        # Camfrog builds have used several IM markers over time.  Detect all of
        # them; a log record makes a new format easy to spot in the startup log.
        is_im = _has_im_marker(line)
        if is_im:
            log.info("IM detected: %r", line[:240])
        m = parse_line(line, self.rx, is_im=is_im)
        if m is None and not is_im:
            m = parse_join(line, self.join_rx)  # "<user> has entered the room"
        return m

    def _recent_nicks(self, lines: list[str], window_s: float = 3 * 3600.0) -> list[str]:
        """Nicks that spoke or joined in *lines* within *window_s* (by the line's
        ``H:MM`` stamp; a line without a stamp counts).  Camfrog's user list is a
        virtual list view whose names cannot be read, so the room history is the
        presence source at startup."""
        seen: dict[str, None] = {}
        for line in lines:
            stamp = re.match(r"^\s*(\d{1,2}:\d{2}(?::\d{2})?)\b", line)
            if stamp and not self._is_recent(stamp.group(1), window_s=window_s):
                continue
            m = parse_line(line, self.rx) or parse_join(line, self.join_rx)
            if m and m.user:
                seen[m.user] = None
        return list(seen)

    def _find(self, ctype, idx):
        """The idx-th control of ctype.  RuntimeError (which messages() retries)
        when it is not there yet -- e.g. a Camfrog window that is still loading.
        A bare IndexError used to escape and end the chat loop for good."""
        found = self.win.descendants(control_type=ctype)
        if not -len(found) <= idx < len(found):
            raise RuntimeError(
                f"chat control {ctype}[{idx}] not found ({len(found)} present); "
                "room window not ready yet, or run AutoDJ.exe --discover"
            )
        return found[idx]

    def _resolve(self):
        """Locate the chat history (and message box) once; remembered until something fails."""
        if self.win is None:
            self._attach()
        if self.cfg.view_kind in ("auto", "web"):
            from ..webchat import find_web_panes

            view, inp = find_web_panes(self.win, self.cfg.web_view_title, self.cfg.web_input_title)
            if view is not None:
                self._web, self._view, self._input = True, view, inp
                self._web_room = True
                self._room_title = _window_title(self.handle)
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

    def _check_room_shown(self) -> None:
        """Raise RoomHiddenError unless the window still shows the room chat.

        Live 2026-11-22: Camfrog switched to its room list (same window, title
        'รายชื่อห้องสนทนา') and for 5 h every send clicked and pasted into that
        page through the cached message-box position, while the reader kept
        re-reading the cached history pane.  Same title: nothing to do (one
        GetWindowTextW).  Changed title (room list, another tab, a new topic):
        the panes are looked up again; none found -> RoomHiddenError.
        """
        title = _window_title(self.handle)
        if self._view is not None and title == self._room_title:
            return
        now = time.monotonic()
        if self._room_hidden and title == self._hidden_title and now - self._hidden_checked < 5.0:
            raise RoomHiddenError(f"Camfrog shows {title!r}, not the room chat")
        from ..webchat import find_web_panes

        if self.win is None:
            self._attach()
        view, inp = find_web_panes(self.win, self.cfg.web_view_title, self.cfg.web_input_title)
        if view is not None:
            self._web, self._view, self._input = True, view, inp
            self._room_title = title
            if self._room_hidden:
                log.info("room chat is shown again (%r): reading and sending resume", title)
                self._room_hidden = False
            return
        self._view = self._input = None  # stale panes of the hidden room page
        self._hidden_title, self._hidden_checked = title, now
        if not self._room_hidden:
            log.warning(
                "Camfrog shows %r instead of the room chat: nothing is read from or "
                "typed into the room until its tab is selected again",
                title,
            )
            self._room_hidden = True
            self._hidden_since = now
        self._maybe_reselect_room_tab(now)
        raise RoomHiddenError(f"Camfrog shows {title!r}, not the room chat")

    def _room_tab_name(self) -> str:
        """The room's tab label: ``room`` from config, else the attached title's prefix."""
        room = (getattr(self.cfg, "room", "") or "").strip()
        if room:
            return room
        return re.split(r"[,:]", self._room_title or "", maxsplit=1)[0].strip()

    def _maybe_reselect_room_tab(self, now: float) -> None:
        """Switch Camfrog back to the room tab when nobody is using the PC.

        Live 2026-11-27 12:50: the window was switched to the room list tab and the
        bot read nothing (room chat, private messages) and posted nothing until a
        person clicked the room tab again. The tab is a native button (class
        CButtonTS) named like the room: BM_CLICK selects it without moving the
        focus (verified live). Only after ROOM_TAB_RESELECT_S hidden, with no
        keyboard/mouse input for ROOM_TAB_IDLE_S (never fight someone browsing the
        room list), at most once per ROOM_TAB_RESELECT_S.
        """
        if now - self._hidden_since < self.ROOM_TAB_RESELECT_S:
            return
        if now - self._tab_tried_at < self.ROOM_TAB_RESELECT_S:
            return
        if _idle_seconds() < self.ROOM_TAB_IDLE_S:
            return
        self._tab_tried_at = now
        name = self._room_tab_name()
        if not name or self.win is None:
            return
        try:
            buttons = self.win.descendants(control_type="Button")
            tab = next(
                (
                    b
                    for b in buttons
                    if b.element_info.name == name and b.element_info.class_name == "CButtonTS"
                ),
                None,
            )
            handle = int(tab.element_info.handle or 0) if tab is not None else 0
        except Exception as ex:  # noqa: BLE001 - COM can fail on a changing page
            log.debug("room tab lookup failed: %s", ex)
            return
        if not handle:
            log.info("room tab %r not found in the Camfrog window; select it by hand", name)
            return
        import ctypes

        windll = getattr(ctypes, "windll", None)
        if windll is None:  # not Windows
            return
        windll.user32.PostMessageW(handle, 0x00F5, 0, 0)  # BM_CLICK
        log.info("selected the room tab %r again (nobody was using the PC)", name)

    def _lines(self) -> list[str]:
        with self.com_lock:
            if self._web_room:
                self._check_room_shown()
            elif self._view is None:
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
            # No IM pane (yet): a new chat window's web pane loads after the window
            # appears, so check again later instead of ignoring this window for good.
            self._im_not_im[w.handle] = time.monotonic() + self.IM_PANE_RECHECK_S
            return []
        lines, nick = got
        if not hasattr(self, "_im_handles"):
            self._im_handles: dict[str, int] = {}
        self._im_handles[nick.lower()] = w.handle  # where send_im() answers this user
        prev = self._im_prev.get(w.handle)
        self._im_prev[w.handle] = lines
        if prev is None and first_scan:
            return []  # baseline: never replay old history
        if not prev:
            # A new window, or one whose pane was still empty when last read: its
            # first message is already in it (diff_lines([], lines) returns nothing,
            # so that message used to be lost).
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
            # windows without an IM pane (room list, popups, a chat still loading) ->
            # when to look at them again
            self._im_not_im: dict[int, float] = {}
        now = time.monotonic()
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
            if self._im_not_im.get(w.handle, 0.0) > now:
                continue
            out.extend(self._im_window_messages(w, first_scan))
        # Forget closed windows (handles are reused by Windows).
        for gone in [h for h in self._im_prev if h not in live]:
            del self._im_prev[gone]
        self._im_not_im = {h: t for h, t in self._im_not_im.items() if h in live}
        handles = getattr(self, "_im_handles", None)
        if handles:  # send_im must never answer into a closed (or reused) window handle
            for nick in [n for n, h in handles.items() if h not in live]:
                del handles[nick]
        return out

    def _room_events(self, prev: list[str] | None, lines: list[str]):
        """ChatMessages for one room read: the first read only reports who is present."""
        if prev is None:
            # First read: the history is a baseline and is never replayed, but
            # the people in it are (most likely) still in the room.  Without
            # this, after a restart everyone already present counted as "not
            # in the room" until they spoke again, and their IM requests were
            # refused (im_require_room_presence).
            yield from self._seen_events(lines)
            return
        if prev and lines and prev[-1] not in lines:
            new = self._after_last_seen(prev, lines)
            if new is None:
                yield from self._seen_events(lines)
                return
        else:
            new = diff_lines(prev, lines)
        for line in new:
            m = self._room_line_message(line)
            if m and m.is_im and not self._im_line_is_recent(line):
                # Live 2026-11-27 12:56: when the room tab was selected again Camfrog
                # re-rendered private messages from 12:19 at the end of the history;
                # they looked new. An old private command must never run again.
                log.info("old private message ignored (history re-render): %r", line[:120])
                continue
            if m:
                yield m

    def _im_line_is_recent(self, line: str) -> bool:
        """True when a room-pane IM line's ``H:MM`` stamp is within IM_MAX_AGE_S."""
        stamp = re.match(r"^\s*(\d{1,2}:\d{2}(?::\d{2})?)\s*([AaPp][Mm])?\b", line)
        if not stamp:
            return True  # no stamp: nothing to judge by
        hhmm = stamp.group(1)
        ampm = (stamp.group(2) or "").lower()
        if ampm:
            parts = hhmm.split(":")
            hour = int(parts[0]) % 12 + (12 if ampm == "pm" else 0)
            hhmm = ":".join([str(hour), *parts[1:]])
        return self._is_recent(hhmm, window_s=self.IM_MAX_AGE_S)

    def _seen_events(self, lines: list[str]):
        for nick in self._recent_nicks(lines):
            yield ChatMessage(nick, "", event="seen")

    @staticmethod
    def _after_last_seen(prev: list[str], lines: list[str]) -> list[str] | None:
        """New lines when the last line we saw is gone; None = take *lines* as a new baseline.

        Camfrog re-rendered, trimmed or reloaded the history (live 2026-11-25 15:34:
        a long line came back split in two; 2026-11-27 05:32: the first read was
        taken while the room page was still loading and shared no line with the
        full history read next). Everything up to the last line the previous read
        also had is history; with no common line at all nothing can be told apart,
        so nothing is replayed: old `!ขอเพลง` commands re-queued songs that had
        already played.
        """
        seen = set(prev)
        anchor = max((i for i, ln in enumerate(lines) if ln in seen), default=-1)
        if anchor < 0:
            log.warning(
                "chat: the room history was replaced (%d line(s), none seen before): "
                "taking it as a new baseline, nothing replayed",
                len(lines),
            )
            return None
        new = lines[anchor + 1 :]
        log.warning(
            "chat: room history re-read (last seen line changed); %d old line(s) ignored, %d new",
            anchor + 1,
            len(new),
        )
        return new

    def _read_room(self) -> list[str] | None:
        """One room read; None when the room page is hidden or the read failed."""
        try:
            return self._lines()
        except RoomHiddenError:
            return None  # room page not shown: keep the baseline, still read IMs
        except Exception as e:  # noqa: BLE001 - COMError is not an OSError: reading must go on
            log.debug("chat read failed: %s", e)
            with self.com_lock:  # protect _view/win against reader/sender race
                self._view = self.win = None  # drop everything: the next poll re-attaches fresh
            return None

    def messages(self):
        prev = None
        while True:
            lines = self._read_room()
            if lines is not None:
                yield from self._room_events(prev, lines)
                prev = lines  # first poll only sets the baseline: old history is never replayed
            # Private messages live in a different web pane; read them even when the
            # room read failed (they used to be skipped then, so no IM arrived).
            try:
                for im in self._im_lines():
                    log.info("IM received: %s: %s", im.user, im.text[:120])
                    yield im
            except Exception:  # noqa: BLE001 - IM reading must never break room chat
                log.debug("IM read failed", exc_info=True)
            time.sleep(self.cfg.poll_interval if lines is not None else 1.0)

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

        _wait_user_idle("Camfrog room window")  # before touching focus or clipboard
        prev = winmsg.foreground()
        try:
            old_clip = pyperclip.paste()
        except (pyperclip.PyperclipException, OSError):
            old_clip = None
        try:
            # No pywinauto restore()/set_focus(): they are cross-process UIA calls, and
            # UIA SetFocus blocked the sender thread for good when Windows refused the
            # focus (live 2026-11-23: no room message after 02:27:49).  _focus_target()
            # restores and raises the window with plain Win32 calls that never block.
            # _ensure_controls() guarantees self._input is not None here
            if self._input is None:  # explicit check: asserts are stripped under python -O
                raise RuntimeError("_ensure_controls must be called before _send_fg")
            handle = int(self.win.handle)
            r = self._input.rectangle()  # measured after the window came forward
            x, y = (r.left + r.right) // 2, (r.top + r.bottom) // 2
            _focus_target(handle, x, y, "Camfrog room window")
            pyperclip.copy(text)  # clipboard paste keeps Thai/Unicode intact
            if self._web:
                self._input.click_input()  # the message box is a web editor: only a click focuses it
                # the web editor takes the focus a moment after the click (~0.35 s
                # measured on the IM editor): do not paste before that
                time.sleep(_WEB_FOCUS_DELAY)
            else:
                self._input.set_focus()
            _still_front(handle, "Camfrog room window")
            _press_ctrl_v()
            time.sleep(_WEB_PASTE_DELAY)
            _still_front(handle, "Camfrog room window")  # never press Enter in another app
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

        Camfrog's IM editor is a WebView2 pane that ignores posted keystrokes, so
        the reply is pasted with the IM window in front.  The IM window is often
        hidden behind the room window: it is brought to the front and the click
        point is checked to be on it *before* anything is typed (a blind click
        landed on the room window and the reply was lost).  Raises RuntimeError
        when the window cannot be used or the line does not show up.
        """
        from pywinauto import Desktop

        from ..webchat import find_web_panes, read_items

        # Wait for the user to stop typing *before* taking com_lock: holding it for
        # up to 30 s stopped every room read and room send meanwhile.
        _wait_user_idle("IM window")
        with self.com_lock:
            handle = getattr(self, "_im_handles", {}).get(user.lower())
            if handle is None:
                raise RuntimeError(f"no open IM window for {user!r}")
            win = Desktop(backend="uia").window(handle=handle)
            view, inp = find_web_panes(win, "wb-log-im-data", self.cfg.web_input_title)
            if view is None or inp is None:
                raise RuntimeError(f"IM window for {user!r} has no message box")

            # Camfrog renders camfrog:join:<room> and URLs as links ("ZeaZDev (Join)"),
            # and the IM reader keeps the text before a link: compare that part.
            expect = re.split(r"camfrog:|https?://", text, maxsplit=1)[0].strip() or text.strip()

            def shown() -> int:
                lines = self._im_pane_lines(read_items(view, tail=60))
                return sum(1 for ln in lines if ln.split("|", 1)[-1].strip() == expect)

            before = shown()
            self._send_im_fg(int(handle), win, inp, text)
            for _ in range(20):  # up to 4 s for Camfrog to render the sent line
                time.sleep(0.2)
                if shown() > before:
                    log.debug("IM sent to %s", user)
                    return
            raise RuntimeError(f"IM to {user!r} was typed but did not appear in the IM window")

    @staticmethod
    def _send_im_fg(handle: int, win, inp, text: str) -> None:
        """Bring the IM window to the front, verify, then type the text + Enter.

        Verified live: Camfrog's IM editor (WebView2) accepts typed keys -- Thai
        included, sent as Unicode key events -- but ignores a clipboard paste,
        and Ctrl+A does not select its text (one editing shortcut even sent the
        draft).  So: click, type, Enter; nothing else.
        """
        import ctypes
        from ctypes import wintypes

        from pywinauto import mouse
        from pywinauto.keyboard import send_keys

        from .. import winmsg

        u32 = ctypes.windll.user32  # type: ignore[attr-defined]
        _wait_user_idle("IM window")  # before touching focus
        prev = winmsg.foreground()
        try:
            if u32.IsIconic(handle):
                u32.ShowWindow(handle, 9)  # SW_RESTORE
            # (no UIA win.set_focus(): it can block forever, see _send_fg)
            deadline = time.monotonic() + 2.0
            while u32.GetForegroundWindow() != handle and time.monotonic() < deadline:
                _bring_to_front(u32, handle)
                time.sleep(0.1)
            if u32.GetForegroundWindow() != handle:
                raise RuntimeError("IM window could not be brought to the front; nothing typed")
            time.sleep(0.15)
            r = inp.rectangle()  # measured now that the window is in front
            x, y = (r.left + r.right) // 2, (r.top + r.bottom) // 2
            hit = u32.WindowFromPoint(wintypes.POINT(x, y))
            if not hit or u32.GetAncestor(hit, 2) != handle:  # GA_ROOT
                raise RuntimeError("IM message box is covered by another window; nothing typed")
            mouse.click(coords=(x, y))  # web editor: only a click focuses it
            time.sleep(0.35)  # WebView2 takes a moment to focus its editor after the click
            if u32.GetForegroundWindow() != handle:
                raise RuntimeError("IM window lost the focus before typing; nothing typed")
            # Drop leftover draft text first, or it is sent glued to the reply.  End +
            # Backspace only: they type no characters and never send (verified live;
            # Ctrl+A does not select in this editor).
            send_keys("{END}{BACKSPACE 120}", pause=0.002)
            send_keys(_keys_literal(text), with_spaces=True, pause=0.005)
            time.sleep(0.15)
            send_keys("{ENTER}")
        finally:
            time.sleep(0.1)
            if prev and prev != handle:
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
        auto (background, then check the line appeared in the room; if not, foreground).
        """
        mode = self.cfg.send_mode
        try:
            if self._web_room:
                self._check_room_shown()  # never type into the room list / another tab
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
            # Compare against the history read *before* typing.  With [] every line of the
            # history counted as new, so an auto-reply posted earlier (they repeat) made
            # a send that never reached the room look delivered.
            before_fg: list[str] = []
            if self.cfg.send_verify:
                try:
                    before_fg = self._lines()
                except (OSError, RuntimeError):
                    before_fg = []
            self._send_fg(text)
            if self.cfg.send_verify and not self._appeared(text, before_fg):
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
        """After 2 unconfirmed background sends in a row, go straight to the foreground
        for ``BG_RETRY_S``: announcements must not stack seconds of verify+fallback
        latency every track. Then background is tried again (it used to stay off for
        the rest of the session)."""
        if mode == "background":
            return True
        with self._bg_fails_lock:
            if self._bg_fails < 2:
                return True
            if time.monotonic() >= self._bg_retry_at:
                self._bg_fails = 0
                log.info("trying background sends again")
                return True
            return False

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
        """Every background attempt failed: count it once, maybe pause background sends."""
        with self._bg_fails_lock:
            self._bg_fails += 1
            bg_fails = self._bg_fails
            if bg_fails >= 2:
                self._bg_retry_at = time.monotonic() + self.BG_RETRY_S
        if mode == "background":
            return "failed"
        log.info(
            "background send not confirmed in the room (%d in a row): falling back to foreground%s",
            bg_fails,
            f"; background paused for {self.BG_RETRY_S / 60:.0f} min" if bg_fails >= 2 else "",
        )
        return "fallback"
