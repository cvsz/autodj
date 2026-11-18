"""Theme system for AutoDJ GUI.

Inspired by TkinterEP (https://github.com/TkinterEP):

* ttkthemes        - theme palettes (adapta, arc, breeze, yaru recommended)
* python-tkextrafont - custom font-file loading for Tkinter
* python-tksvg     - SVG image support in Tkinter
* ttkwidgets       - enhanced widget concepts

Nothing from TkinterEP is a hard dependency (ttkthemes is GPL-3.0).  This module
re-implements the useful ideas as optional, MIT-friendly helpers so AutoDJ
stays license-safe while looking like a modern music player.

Usage::

    from .theme import Theme, apply_theme, load_font, svg_image

    theme = Theme("zplayer-dark")
    apply_theme(root, theme)
    f = load_font("assets/Inter-Regular.ttf", 11)
    img = svg_image("assets/play.svg", 24, 24)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:  # pragma: no cover - typing only; keeps headless imports tkinter-free
    from tkinter import PhotoImage
    from tkinter import font as tkfont

# NOTE: tkinter is imported lazily inside the helpers below on purpose.
# config.py imports THEMES at module load, and the GUI test suite swaps in a
# strict fake `tkinter` module.  A module-level tkinter import would bind this
# module to whichever copy happened to be first, mixing real and fake Tk.

# ---------------------------------------------------------------------------
# Palettes inspired by TkinterEP / ttkthemes (adapta, arc, breeze, yaru)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Palette:
    """A complete colour scheme for the GUI."""

    name: str
    # Structural
    bg: str  # window / app background
    surface: str  # card / panel background
    surface2: str  # elevated card / input background
    border: str  # subtle divider
    border_focus: str  # focused border
    # Text
    text: str  # primary text
    muted: str  # secondary text
    inverse: str  # text on dark accent
    # Accents
    primary: str  # brand / primary action
    primary_hover: str
    success: str  # play / on-air
    warning: str  # caution
    danger: str  # stop / error
    # State
    on_air: str  # playing indicator
    idle: str  # stopped indicator
    # Special
    glow: str  # animated glow tint
    cyan: str = "#38bdf8"  # secondary accent used by the zPlayer dashboard


# zPlayer-dark: the default AutoDJ dashboard theme (dark studio look).
# Inspired by the "adapta" / "arc" dark themes from ttkthemes.
ZPLAYER_DARK = Palette(
    name="zplayer-dark",
    bg="#0a0b12",
    surface="#161a26",
    surface2="#1e2436",
    border="#2d364a",
    border_focus="#7c5cff",
    text="#e8eaed",
    muted="#8b93a6",
    inverse="#0a0b12",
    primary="#7c5cff",
    primary_hover="#957dff",
    success="#34d399",
    warning="#fbbf24",
    danger="#f87171",
    on_air="#ff4da6",
    idle="#8b93a6",
    glow="#7c5cff",
    cyan="#38bdf8",
)

# zPlayer-neon: vibrant cyberpunk variant.
ZPLAYER_NEON = Palette(
    name="zplayer-neon",
    bg="#050508",
    surface="#0f0f1a",
    surface2="#1a1a2e",
    border="#2a2a4a",
    border_focus="#00f2ff",
    text="#ffffff",
    muted="#9ca3af",
    inverse="#050508",
    primary="#00f2ff",
    primary_hover="#4df5ff",
    success="#00ff88",
    warning="#ffd166",
    danger="#ff4757",
    on_air="#ff00ff",
    idle="#64748b",
    glow="#00f2ff",
    cyan="#00f2ff",
)

# zPlayer-light: clean daylight variant (inspired by "yaru" / "breeze" light).
ZPLAYER_LIGHT = Palette(
    name="zplayer-light",
    bg="#f8fafc",
    surface="#ffffff",
    surface2="#f1f5f9",
    border="#cbd5e1",
    border_focus="#7c5cff",
    text="#1e293b",
    muted="#64748b",
    inverse="#ffffff",
    primary="#7c5cff",
    primary_hover="#6d4ed6",
    success="#10b981",
    warning="#eab308",
    danger="#ef4444",
    on_air="#ec4899",
    idle="#94a3b8",
    glow="#7c5cff",
    cyan="#7c5cff",
)

# All built-in themes.
THEMES: dict[str, Palette] = {
    "zplayer-dark": ZPLAYER_DARK,
    "zplayer-neon": ZPLAYER_NEON,
    "zplayer-light": ZPLAYER_LIGHT,
}


@dataclass
class Theme:
    """Active theme: palette + fonts + optional assets."""

    palette: Palette
    font_family: str = "Segoe UI"
    font_fallback: str = "TkDefaultFont"
    icon_size: int = 18
    icon_font_family: str = "Segoe UI Symbol"
    loaded_fonts: dict = field(default_factory=dict)

    @classmethod
    def from_name(cls, name: str) -> "Theme":
        pal = THEMES.get(name, ZPLAYER_DARK)
        return cls(palette=pal)

    def font(
        self, size: int, weight: Literal["normal", "bold"] = "normal", family: str | None = None
    ) -> tkfont.Font:
        """Return a cached tkinter Font for *size* / *weight*."""
        from tkinter import font as tkfont

        fam = family or self.font_family
        key = (fam, size, weight)
        if key not in self.loaded_fonts:
            self.loaded_fonts[key] = tkfont.Font(
                family=fam,
                size=size,
                weight=weight,
            )
        return self.loaded_fonts[key]


# ---------------------------------------------------------------------------
# Custom font loading (python-tkextrafont pattern)
# ---------------------------------------------------------------------------


def load_font(
    path: str | os.PathLike[str],
    size: int,
    weight: Literal["normal", "bold"] = "normal",
    family: str | None = None,
    root=None,
) -> tkfont.Font | None:
    """Load a TTF/OTF font file and return a tkinter Font, or None on failure.

    Mirrors the idea of TkinterEP/python-tkextrafont (loading custom font
    files into Tkinter) without the C extension -- tkinter can use any font
    already installed on the system by family name.  This helper lets you
    reference a bundled font file; on platforms where Tk supports font
    embedding (Tcl 8.6+ with the `font create` mechanism) the file is
    registered, otherwise we fall back to the family name.
    """
    import tkinter as tk
    from tkinter import font as tkfont

    p = Path(path)
    if not p.exists():
        return None
    fam = family or p.stem
    try:
        if root is not None:
            # Try to register the font file with Tk (Tk 8.6+).
            root.tk.call(
                "font",
                "create",
                fam,
                "-file",
                str(p),
                "-size",
                str(size),
                "-weight",
                weight,
            )
        return tkfont.Font(family=fam, size=size, weight=weight)
    except (tk.TclError, AttributeError, OSError):
        # Fall back to system font by family name.
        try:
            return tkfont.Font(family=fam, size=size, weight=weight)
        except tk.TclError:
            return None


# ---------------------------------------------------------------------------
# SVG image support (python-tksvg pattern)
# ---------------------------------------------------------------------------


def svg_image(
    path: str | os.PathLike[str], width: int, height: int, root=None
) -> PhotoImage | None:
    """Load an SVG as a PhotoImage, or None if tksvg is unavailable.

    Mirrors TkinterEP/python-tksvg.  Requires the optional ``tksvg`` package
    (pip install python-tksvg).  Without it, returns None and callers should
    fall back to emoji / text icons.
    """
    try:
        from tksvg import SvgImage  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        return SvgImage(path=Path(path), width=width, height=height)
    except Exception:  # noqa: BLE001 - optional asset, never fatal
        return None


# ---------------------------------------------------------------------------
# Apply theme to a tkinter root
# ---------------------------------------------------------------------------


def apply_theme(root, theme: Theme) -> None:
    """Apply *theme* to *root*: ttk scrollbar style, option database, etc."""
    import tkinter as tk
    from tkinter import ttk

    p = theme.palette
    s = getattr(root, "ttk_style", None)
    if s is None:
        s = ttk.Style(root)
        root.ttk_style = s  # type: ignore[attr-defined]
    try:
        s.theme_use("clam")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001,S110 - best-effort theme switch; clam is a fallback
        pass

    def _cfg(style: str, **kw):
        try:
            s.configure(style, **kw)  # type: ignore[attr-defined]
        except tk.TclError:
            pass

    _cfg(
        "Vertical.TScrollbar",
        background=p.surface2,
        troughcolor=p.bg,
        bordercolor=p.border,
        arrowcolor=p.muted,
        lightcolor=p.surface2,
        darkcolor=p.surface2,
        relief="flat",
    )
    s.map("Vertical.TScrollbar", background=[("active", p.border)])  # type: ignore[attr-defined]
    _cfg(
        "Horizontal.TScrollbar",
        background=p.surface2,
        troughcolor=p.bg,
        bordercolor=p.border,
        arrowcolor=p.muted,
        lightcolor=p.surface2,
        darkcolor=p.surface2,
        relief="flat",
    )
    s.map("Horizontal.TScrollbar", background=[("active", p.border)])  # type: ignore[attr-defined]
    _cfg(
        "TCombobox",
        fieldbackground=p.surface2,
        background=p.surface2,
        foreground=p.text,
        arrowcolor=p.muted,
        bordercolor=p.border,
        lightcolor=p.surface2,
        darkcolor=p.surface2,
    )
    s.map(  # type: ignore[attr-defined]
        "TCombobox",
        fieldbackground=[("readonly", p.surface2)],
        selectbackground=[("readonly", p.primary)],
        selectforeground=[("readonly", p.inverse)],
    )

    # Option database for classic widgets (tk.Label, tk.Entry, tk.Text, ...).
    # ``option_add`` is absent on the strict fake Tk used by the logic tests.
    add_option = getattr(root, "option_add", None)
    if add_option is not None:
        # Tcl font specs need braces when the family contains spaces, e.g.
        # ``{Segoe UI} 10`` -- otherwise Tcl reads "UI" as the size.
        add_option("*Font", f"{{{theme.font_family}}} 10")
        add_option("*Background", p.surface)
        add_option("*Foreground", p.text)
        add_option("*selectBackground", p.primary)
        add_option("*selectForeground", p.inverse)
        add_option("*insertBackground", p.primary)
        add_option("*highlightBackground", p.border)
        add_option("*highlightColor", p.border_focus)
