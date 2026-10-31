"""Tk-free key mapping for Ctrl+C/V/X/A on any keyboard layout (used by gui.py)."""

from __future__ import annotations

# Windows virtual-key codes. Tk matches <Control-v> by keysym, which is a Thai letter on a Thai keyboard
# layout, so Ctrl+C/V/X/A silently did nothing. We match the physical key (keycode) instead.
_VK_ACTIONS = {
    67: "copy",
    86: "paste",
    88: "cut",
    65: "all",
    45: "paste",
}  # 45 = Insert (Shift+Insert)


def clip_action(keycode: int, keysym: str, shift: bool = False, windows: bool = True):
    """Action for a Ctrl(+Shift)+key press, only when Tk's own binding will NOT fire (non-Latin layout);
    otherwise None so we never double-paste. Ctrl+Insert = copy, Shift+Insert = paste."""
    if not windows:
        return None
    if keycode == 45:
        return "copy" if not shift else "paste"
    act = _VK_ACTIONS.get(keycode)
    if act is None or keysym.lower() in ("c", "v", "x", "a"):
        return None
    return act
