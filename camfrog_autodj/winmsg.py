"""Background chat input: post window messages straight to the chat window's own HWND, so Camfrog never
has to come to the foreground and the keyboard/clipboard are left alone. Win32 only; the pure helpers at
the top are platform independent (and unit-tested)."""
from __future__ import annotations
import logging
import time

from .textutil import clean_text

log = logging.getLogger("autodj")

WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP = 0x0200, 0x0201, 0x0202
WM_KEYDOWN, WM_KEYUP, WM_CHAR = 0x0100, 0x0101, 0x0102
VK_RETURN, MK_LBUTTON = 0x0D, 0x0001


def utf16_units(text: str) -> list[int]:
    """WM_CHAR carries UTF-16 code units (Thai = 1 unit, emoji = surrogate pair)."""
    b = text.encode("utf-16-le")
    return [int.from_bytes(b[i:i + 2], "little") for i in range(0, len(b), 2)]


def make_lparam(x: int, y: int) -> int:
    return ((y & 0xFFFF) << 16) | (x & 0xFFFF)


def pick_child(rects: list[tuple[int, tuple[int, int, int, int]]], pt: tuple[int, int]) -> int | None:
    """Handle of the smallest window whose rect contains pt (the deepest control under the point)."""
    best, best_area = None, None
    for h, (l, t, r, b) in rects:
        if l <= pt[0] < r and t <= pt[1] < b:
            a = (r - l) * (b - t)
            if best_area is None or a < best_area:
                best, best_area = h, a
    return best


# ---- Win32 -------------------------------------------------------------------------------------

def _u32():
    import ctypes
    from ctypes import wintypes as w
    u = ctypes.windll.user32
    u.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
    u.PostMessageW.restype = w.BOOL
    u.GetForegroundWindow.restype = w.HWND
    u.SetForegroundWindow.argtypes = [w.HWND]
    u.IsIconic.argtypes = [w.HWND]
    u.ShowWindow.argtypes = [w.HWND, ctypes.c_int]
    u.IsWindowVisible.argtypes = [w.HWND]
    u.GetWindowRect.argtypes = [w.HWND, ctypes.POINTER(w.RECT)]
    u.ScreenToClient.argtypes = [w.HWND, ctypes.POINTER(w.POINT)]
    return u


def child_rects(top: int) -> list[tuple[int, tuple[int, int, int, int]]]:
    import ctypes
    from ctypes import wintypes as w
    u = _u32()
    out = []
    cb_t = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)

    def cb(h, _lp):
        if u.IsWindowVisible(h):
            r = w.RECT()
            if u.GetWindowRect(h, ctypes.byref(r)):
                out.append((int(h or 0), (r.left, r.top, r.right, r.bottom)))
        return True

    u.EnumChildWindows(top, cb_t(cb), 0)
    return out


def show_noactivate(hwnd: int):
    """Un-minimise without stealing focus."""
    u = _u32()
    if u.IsIconic(hwnd):
        u.ShowWindow(hwnd, 4)  # SW_SHOWNOACTIVATE
        time.sleep(0.3)


def post_text(top: int, screen_pt: tuple[int, int], text: str, enter: bool = True,
              click: bool = True, delay: float = 0.004) -> bool:
    """Click the editor at screen_pt and type `text` (+ Enter) with posted messages. No focus change.
    Returns True if every message was queued (this does NOT prove the page accepted it)."""
    import ctypes
    from ctypes import wintypes as w
    u = _u32()
    target = pick_child(child_rects(top), screen_pt) or top
    pt = w.POINT(*screen_pt)
    u.ScreenToClient(target, ctypes.byref(pt))
    lp = make_lparam(pt.x, pt.y)
    ok = True

    def post(msg, wp=0, lparam=0):
        nonlocal ok
        ok = bool(u.PostMessageW(target, msg, wp, lparam)) and ok

    if click:  # gives the page's editor DOM focus without activating the window
        post(WM_MOUSEMOVE, 0, lp)
        post(WM_LBUTTONDOWN, MK_LBUTTON, lp)
        post(WM_LBUTTONUP, 0, lp)
        time.sleep(0.05)
    for unit in utf16_units(clean_text(text)):  # no control characters typed into the room
        post(WM_CHAR, unit, 1)
        time.sleep(delay)
    if enter:
        time.sleep(0.03)
        post(WM_KEYDOWN, VK_RETURN, 0x001C0001)
        post(WM_CHAR, 13, 0x001C0001)
        post(WM_KEYUP, VK_RETURN, 0xC01C0001)
    log.debug("posted %d chars to hwnd %s (top %s): %s", len(text), target, top, "ok" if ok else "FAILED")
    return ok


def foreground() -> int:
    return int(_u32().GetForegroundWindow() or 0)


def restore_foreground(hwnd: int):
    if hwnd:
        try:
            _u32().SetForegroundWindow(hwnd)
        except Exception:
            pass
