"""Find Camfrog top-level windows without tripping over pywinauto's ElementAmbiguousError.
`.*Camfrog.*` normally matches several windows (main client, room window, hidden helper
windows), so we enumerate, filter, and pick one deterministically."""
from __future__ import annotations
import logging
import os
import re
import time
from dataclasses import dataclass

log = logging.getLogger("autodj")


DEFAULT_EXE_RE = "(?i)camfrog"  # only windows owned by a process whose exe name matches (not browser tabs)


@dataclass
class Cand:
    handle: int
    title: str
    cls: str
    pid: int
    exe: str = ""


def exe_name(pid: int) -> str:
    """Executable file name of a process (Windows), '' if it cannot be read."""
    try:
        import ctypes
        from ctypes import wintypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(1024)
            n = wintypes.DWORD(1024)
            if k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
                return os.path.basename(buf.value)
        finally:
            k.CloseHandle(h)
    except Exception:
        pass
    return ""


def pick(cands: list[Cand], exclude_re: str = "", prefer: str = "", index: int = 0,
         self_pid: int | None = None, exe_re: str = "") -> Cand | None:
    """Pure selection logic. Drops our own process and anything matching exclude_re,
    puts titles containing `prefer` (e.g. the room name) first, then takes [index]."""
    out = [c for c in cands if c.pid != self_pid]
    if exe_re:
        xr = re.compile(exe_re)
        out = [c for c in out if xr.search(c.exe)]
    if exclude_re:
        rx = re.compile(exclude_re)
        out = [c for c in out if not rx.search(c.title)]
    if prefer:
        out.sort(key=lambda c: prefer.lower() not in c.title.lower())  # stable
    if not out:
        return None
    return out[min(max(index, 0), len(out) - 1)]


def candidates(pattern: str, visible_only: bool = True, exe_re: str = "") -> list[Cand]:
    from pywinauto import findwindows
    els = findwindows.find_elements(title_re=pattern, top_level_only=True,
                                    backend="uia", visible_only=visible_only)
    out = [Cand(e.handle, e.name or "", e.class_name or "", e.process_id) for e in els]
    for c in out:
        c.exe = exe_name(c.pid)
    if exe_re:
        xr = re.compile(exe_re)
        out = [c for c in out if xr.search(c.exe)]
    return out


def resolve(pattern: str, exclude_re: str = "", prefer: str = "", index: int = 0,
            timeout: float = 30, exe_re: str | None = None) -> Cand | None:
    exe_re = DEFAULT_EXE_RE if exe_re is None else exe_re
    end = time.time() + timeout
    while True:
        cs = candidates(pattern, exe_re=exe_re)
        c = pick(cs, exclude_re, prefer, index, os.getpid())
        if c:
            if len(cs) > 1:
                log.info("%d windows match %r; using %r (pid %s). Others: %s", len(cs), pattern,
                         c.title, c.pid, [x.title for x in cs if x is not c])
            return c
        if time.time() >= end:
            return None
        time.sleep(1)


def list_all() -> list[Cand]:
    """Every visible top-level window with its process exe (for diagnosing what Camfrog looks like)."""
    return candidates(".*", visible_only=True)
