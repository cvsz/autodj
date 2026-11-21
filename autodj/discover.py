"""Auto-discover the Camfrog room window and its chat controls, and write them to config.toml.
Replaces the manual tools/inspect_ui.py step: finds window_title_re, view_type/view_index and
input_type/input_index. The selection logic is pure (testable); only scan_window touches Windows.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import tomllib
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("autodj")

VIEW_TYPES = ("Document", "Edit")
INPUT_TYPES = ("Edit",)


@dataclass
class Ctl:
    ctype: str
    index: int  # index inside window.descendants(control_type=ctype): what config stores
    text: str = ""
    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0
    enabled: bool = True
    visible: bool = True

    @property
    def area(self) -> int:
        return max(0, self.right - self.left) * max(0, self.bottom - self.top)

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)


def choose_view(ctls: list[Ctl], rx: re.Pattern) -> tuple[Ctl | None, int]:
    """Chat history = the control whose text has the most lines like `user: text`
    (then longest text, then biggest area). Returns (control, matched_line_count)."""
    best, best_key = None, None
    for c in ctls:
        if c.ctype not in VIEW_TYPES or not c.visible:
            continue
        matched = sum(1 for ln in c.text.splitlines() if rx.match(ln.strip()))
        key = (matched, len(c.text), c.area, c.ctype == "Document")
        if best_key is None or key > best_key:
            best, best_key = c, key
    if best is None or best_key is None:
        return None, 0
    if best_key[0] == 0 and best.ctype != "Document":
        # No chat-like lines matched: not a chat view.
        return None, 0
    return best, best_key[0]


def choose_input(ctls: list[Ctl], view: Ctl | None) -> Ctl | None:
    """Message box = enabled, visible Edit (not the chat view) lowest on screen, widest wins ties."""
    cands = [
        c
        for c in ctls
        if c.ctype in INPUT_TYPES
        and c.visible
        and c.enabled
        and not (view and c.ctype == view.ctype and c.index == view.index)
    ]
    if not cands:
        return None
    return max(cands, key=lambda c: (c.top, c.width))


@dataclass
class Found:
    title: str
    view: Ctl
    input: Ctl
    matched: int
    web: bool = False


def score_window(title: str, ctls: list[Ctl], rx: re.Pattern) -> Found | None:
    view, matched = choose_view(ctls, rx)
    if view is None:
        return None
    if matched == 0:
        # A Document + Edit without a single chat line is not evidence of a room:
        # Camfrog's room list ("รายชื่อห้องสนทนา") has exactly that shape (list +
        # search box).  Accepting it made auto-discover overwrite a working
        # window_title_re with the room list whenever the room window was closed,
        # and the bot then failed every send ("no pane titled like 'wb-log-room-data'").
        return None
    inp = choose_input(ctls, view)
    if inp is None:
        return None
    return Found(title, view, inp, matched)


def score_web(title: str, win, cfg, rx: re.Pattern) -> Found | None:
    """Camfrog room window: chat history and message box are embedded-web panes (see webchat.py)."""
    from .webchat import find_web_panes, read_web

    view, inp = find_web_panes(win, cfg.web_view_title, cfg.web_input_title)
    if view is None or inp is None:
        return None
    lines = read_web(view, strict=cfg.web_strict_body)
    matched = sum(1 for ln in lines if rx.match(ln))
    return Found(title, Ctl("Pane", 0), Ctl("Pane", 0), matched, web=True)


def best_room(found: list[Found]) -> Found | None:
    # most parsed chat lines first; ties -> larger chat view
    return max(found, key=lambda f: (f.matched, f.view.area), default=None) if found else None


def to_updates(f: Found) -> dict:
    if f.web:
        return {"window_title_re": re.escape(f.title), "view_kind": "web"}
    return {
        "window_title_re": re.escape(f.title),
        "view_type": f.view.ctype,
        "view_index": f.view.index,
        "input_type": f.input.ctype,
        "input_index": f.input.index,
    }


# ---- Windows side -------------------------------------------------------------------------


def scan_window(win) -> list[Ctl]:
    from .adapters.uia import _read

    out: list[Ctl] = []
    for ctype in ("Document", "Edit"):
        try:
            items = win.descendants(control_type=ctype)
        except (AttributeError, RuntimeError):
            continue
        for i, c in enumerate(items):
            try:
                r = c.rectangle()
                box = (r.left, r.top, r.right, r.bottom)
            except (AttributeError, RuntimeError):
                box = (0, 0, 0, 0)
            try:
                vis, ena = bool(c.is_visible()), bool(c.is_enabled())
            except (AttributeError, RuntimeError):
                vis = ena = True
            try:
                text = _read(c)
            except Exception as ex:  # NoPatternInterfaceError / NULL COM pointer:
                log.debug(
                    "discover: skip %s[%d] (%s)", ctype, i, ex
                )  # one bad control must not abort the scan
                continue
            out.append(Ctl(ctype, i, text, *box, enabled=ena, visible=vis))
    return out


def discover(cfg) -> dict | None:
    """Scan every visible Camfrog window and return config updates for the best room, or None."""
    try:
        from pywinauto import Desktop
    except (
        ImportError,
        PermissionError,
    ):  # pywinauto is Windows-only; may be absent on other platforms
        # PermissionError from comtypes gen-dir write failure when pywinauto is
        # absent/broken on the current platform also counts as "not available"
        log.warning(
            "auto-discover: pywinauto is not available (ImportError or PermissionError); "
            "cannot scan Camfrog windows"
        )
        return None

    from .windows import candidates

    rx = re.compile(cfg.line_regex)
    found: list[Found] = []
    cands = [c for c in candidates(".*", exe_re=cfg.process_re) if c.pid != os.getpid()]
    log.info(
        "auto-discover: scanning %d window(s) of processes matching %r: %s",
        len(cands),
        cfg.process_re,
        [c.title for c in cands],
    )
    if not cands:
        log.warning(
            "auto-discover: no such window. Run `AutoDJ.exe --windows` to see every window "
            "and its exe; adjust process_re to match the Camfrog exe"
        )
    for c in cands:
        try:
            win = Desktop(backend="uia").window(handle=c.handle)
            f = score_web(c.title, win, cfg, rx) or score_window(c.title, scan_window(win), rx)
        except Exception as e:  # a window can vanish or expose no UIA patterns mid-scan
            log.debug("skip %r: %s", c.title, e)
            continue
        if f:
            log.info(
                "candidate %r: %s (%d chat lines)",
                c.title,
                (
                    "web chat view + message box"
                    if f.web
                    else f"chat={f.view.ctype}[{f.view.index}] input={f.input.ctype}[{f.input.index}]"
                ),
                f.matched,
            )
            found.append(f)
    best = best_room(found)
    return to_updates(best) if best else None


# ---- config.toml editing (keeps comments and layout) -------------------------------------


def _toml_value(v) -> str:
    """Convert a Python value to a TOML basic string, preserving validity.

    Rules:
    - bool/int: native TOML
    - str without control chars and no single quotes → single-quoted TOML
    - str with backslashes → double-quoted TOML (backslashes are escape seqs)
    - str with single quotes or control chars → double-quoted with escapes
    """
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    s = str(v)
    has_bs = "\\" in s
    has_single = "'" in s
    has_ctrl = any(ord(c) < 32 or ord(c) == 127 for c in s)
    # If the string has backslashes, use double quotes so they're proper escape seqs.
    # Otherwise, single-quoted TOML is more readable and preserves literal backslashes.
    if not has_single and not has_ctrl and not has_bs:
        return f"'{s}'"
    # Double-quoted: escape backslash, double-quote, newline, carriage-return, tab
    esc = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\r": "\\r", "\t": "\\t"}
    return (
        '"'
        + "".join(
            esc.get(c, c if ord(c) >= 32 and ord(c) != 127 else f"\\u{ord(c):04x}") for c in s
        )
        + '"'
    )


def update_config_text(text: str, updates: dict[str, object]) -> str:
    lines = text.splitlines()
    for key, val in updates.items():
        new = f"{key} = {_toml_value(val)}"
        # Match: key = value (quoted or unquoted, optionally followed by comment)
        # Value match is lazy (+?) so spaces before a trailing # comment are preserved
        rx = re.compile(
            rf"^(\s*){re.escape(key)}\s*=\s*(?:'[^']*'|\"(?:[^\"\\]|\\.)*\"|[^#\n]+?)(\s*#.*)?$"
        )
        for i, ln in enumerate(lines):
            m = rx.match(ln)
            if m:
                # Preserve the original line when the new value is semantically
                # equal (avoid changing double→single quotes or vice versa).
                old_val_part = m.group(0).split("=", 1)[1].strip()
                old_val_part = old_val_part.split(" #")[0].strip()
                try:
                    old_d = tomllib.loads(f"{key} = {old_val_part}")
                    new_d = tomllib.loads(new)
                    if old_d.get(key) == new_d.get(key):
                        # Keep the original line, but stop scanning for this
                        # key: `continue` would fall through to the `else`
                        # clause below and append a duplicate TOML key.
                        break
                except (tomllib.TOMLDecodeError, ValueError):
                    pass  # value comparison failed; update anyway
                lines[i] = m.group(1) + new + (m.group(2) or "")
                break
        else:
            lines.append(new)
    return "\n".join(lines) + "\n"


def save_config(path: str, updates: dict) -> bool:
    """Write updates into config.toml (backup in config.toml.bak). Returns True if the file changed."""
    p = Path(path)
    try:
        old = p.read_text("utf-8") if p.exists() else ""
    except OSError as ex:
        log.warning(
            "auto-discover: NOT saving to %s, cannot read config file (%s)",
            path,
            ex,
        )
        return False
    new = update_config_text(old, updates)
    if new == old:
        return False
    try:
        tomllib.loads(
            new
        )  # never replace a working config with one AutoDJ itself could not read back
    except tomllib.TOMLDecodeError as ex:
        log.warning(
            "auto-discover: NOT saving to %s, the result would not be valid TOML (%s)",
            path,
            ex,
        )
        return False
    try:
        if p.exists():
            shutil.copyfile(p, p.with_name(p.name + ".bak"))
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text(new, "utf-8")
        if os.name != "nt":  # config may hold webhook_secret / ai_api_key
            os.chmod(tmp, 0o600)
        os.replace(tmp, p)  # atomic: a crash mid-write cannot leave half a file
    except OSError as ex:  # permission denied, read-only file, etc.
        log.warning(
            "auto-discover: NOT saving to %s, cannot write config file (%s)",
            path,
            ex,
        )
        return False
    return True


def apply(cfg, path: str) -> dict | None:
    """Discover, update cfg in memory and config.toml. Returns the updates (or None if nothing found)."""
    ups = discover(cfg)
    if not ups:
        log.warning("auto-discover: no Camfrog room chat found (open the room window first)")
        return None
    for k, v in ups.items():
        setattr(cfg, k, v)
    changed = save_config(path, ups)
    log.info("auto-discover: %s %s", "updated" if changed else "unchanged", path)
    return ups
