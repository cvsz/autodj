"""Tk desktop window for the engine: a dark "studio" look with a spinning record, an animated equaliser,
glowing progress/volume bars and a tabbed queue / history / chat panel.
Polls Engine.snapshot() twice a second (data) and animates at ~30 fps (looks only); all actions call engine methods.
The equaliser is decorative: it moves while a track plays and settles when paused; it does not analyse the audio."""

from __future__ import annotations

import logging
import math
import os
import time
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter import font as tkfont

from .clipkeys import clip_action
from .library import MEDIA
from .visuals import (
    aurora_offset,
    bar_heights,
    confetti_burst,
    confetti_pos,
    ease,
    gradient,
    lerp_color,
    make_particles,
    particle_pos,
    pulse,
    round_rect_points,
)

log = logging.getLogger("autodj")

# palette
BG, SURFACE, SURFACE2, BORDER = "#06070d", "#121628", "#1a2038", "#2a3256"
AURORA = [
    "#1a0a2e",
    "#140a30",
    "#0a1a3a",
    "#0a2a2e",
    "#1a0a2e",
]  # deep backdrop bands, drift slowly
TEXT, MUTED = "#eef1ff", "#8d95bb"
PINK, VIOLET, CYAN, GREEN, RED = "#ff3d9a", "#8a5cff", "#27e1ff", "#35e08c", "#ff4d6d"
FAMILY = "Segoe UI"
FPS_MS = 33


def mmss(sec: float) -> str:
    s = int(sec)
    return f"{s // 60}:{s % 60:02d}"


def _do_clip(w, act: str):
    try:
        if act == "all":
            if isinstance(w, tk.Text):
                w.tag_add("sel", "1.0", "end-1c")
            else:
                w.select_range(0, "end")
                w.icursor("end")
        else:
            w.event_generate(
                {"copy": "<<Copy>>", "cut": "<<Cut>>", "paste": "<<Paste>>"}[act]
            )
    except tk.TclError:
        pass


def install_clipboard(root: tk.Misc, lang=lambda: "en"):
    """Ctrl+C/V/X/A on any keyboard layout, right-click menu (Cut/Copy/Paste/Select all) on every entry
    and text box, and click-to-focus on the read-only chat log so it can be selected and copied."""

    def on_key(e):
        act = clip_action(e.keycode, e.keysym, bool(e.state & 0x1), os.name == "nt")
        if act and isinstance(
            e.widget, (tk.Entry, tk.Text, ttk.Entry, ttk.Combobox, ttk.Spinbox)
        ):
            _do_clip(e.widget, act)
            return "break"

    def menu(e):
        w = e.widget
        w.focus_set()
        th = lang() == "th"
        m = tk.Menu(w, tearoff=0)
        for act, en, thai in (
            ("cut", "Cut", "ตัด"),
            ("copy", "Copy", "คัดลอก"),
            ("paste", "Paste", "วาง"),
            ("all", "Select all", "เลือกทั้งหมด"),
        ):
            m.add_command(
                label=thai if th else en, command=lambda a=act: _do_clip(w, a)
            )
        m.tk_popup(e.x_root, e.y_root)
        return "break"

    root.bind_all("<Control-KeyPress>", on_key, add="+")
    root.bind_all("<Control-Shift-KeyPress>", on_key, add="+")
    for cls in ("Entry", "TEntry", "Text", "TCombobox", "TSpinbox"):
        root.bind_class(cls, "<Button-3>", menu, add="+")
    root.bind_class("Text", "<Button-1>", lambda e: e.widget.focus_set(), add="+")


class PillButton(tk.Canvas):
    """Rounded button drawn on a canvas. Behaves like a Button for the pieces the app uses:
    configure(text=..., command=...), cget("text"), plus set_active() for tabs/toggle chips and set_icon()."""

    STYLES = {  # kind: (fill, hover fill, outline, text colour, active fill, active outline, active text)
        "primary": (PINK, "#ff62b0", "", "#ffffff", PINK, "", "#ffffff"),
        "ghost": (SURFACE2, "#232b4a", BORDER, TEXT, SURFACE2, BORDER, TEXT),
        "tab": (SURFACE, SURFACE2, "", MUTED, "#241b4d", VIOLET, TEXT),
        "chip": (SURFACE2, "#232b4a", BORDER, MUTED, "#0f2a35", CYAN, CYAN),
        "danger": (SURFACE2, "#2d1f33", RED, RED, SURFACE2, RED, RED),
    }

    def __init__(
        self,
        parent,
        text="",
        command=None,
        kind="ghost",
        icon="",
        font=None,
        icon_font=None,
        bg=SURFACE,
        minw=0,
        height=38,
        padx=16,
    ):
        tk.Canvas.__init__(
            self,
            parent,
            width=max(minw, 40),
            height=height,
            bg=bg,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self._text, self._cmd, self._look, self._icon = text, command, kind, icon
        self._font = font or tkfont.nametofont("TkDefaultFont")
        self._ifont = icon_font or self._font
        self._minw, self._h, self._padx = minw, height, padx
        self._hover = self._down = self._active = False
        self.bind("<Enter>", lambda _e: self._hov(True))
        self.bind("<Leave>", lambda _e: self._hov(False))
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self._draw()

    # --- Button-like API
    def configure(self, cnf=None, **kw):
        if isinstance(cnf, dict):
            kw = {**cnf, **kw}
            cnf = None
        redraw = False
        if "text" in kw:
            self._text = kw.pop("text")
            redraw = True
        if "command" in kw:
            self._cmd = kw.pop("command")
        if redraw:
            self._draw()
        if kw or cnf:
            return tk.Canvas.configure(self, cnf, **kw)
        return None

    config = configure

    def cget(self, key):
        return self._text if key == "text" else tk.Canvas.cget(self, key)

    def set_active(self, on: bool):
        if bool(on) != self._active:
            self._active = bool(on)
            self._draw()

    def set_icon(self, icon: str):
        if icon != self._icon:
            self._icon = icon
            self._draw()

    # --- interaction
    def _hov(self, v):
        self._hover = v
        if not v:
            self._down = False
        self._draw()

    def _press(self, _e):
        self._down = True
        self._draw()

    def _release(self, e):
        was = self._down
        self._down = False
        self._draw()
        if (
            was
            and self._cmd
            and 0 <= e.x <= int(self.winfo_width() or 9999)
            and 0 <= e.y <= self._h
        ):
            self._cmd()

    # --- drawing
    def _draw(self):
        fill, hov, line, fg, afill, aline, afg = self.STYLES[self._look]
        if self._active:
            fill, line, fg = afill, aline, afg
        if self._hover:
            fill = hov if not self._active else lerp_color(fill, "#ffffff", 0.08)
        if self._down:
            fill = lerp_color(fill, "#000000", 0.25)
        iw = self._ifont.measure(self._icon) + 8 if self._icon else 0
        tw = self._font.measure(self._text)
        w = max(self._minw, iw + tw + 2 * self._padx)
        tk.Canvas.configure(self, width=w)
        self.delete("all")
        self.create_polygon(
            round_rect_points(1, 1, w - 1, self._h - 1, self._h / 2),
            smooth=True,
            fill=fill,
            outline=line,
            width=1,
        )
        x = (w - (iw + tw)) / 2
        if self._icon:
            self.create_text(
                x, self._h / 2, text=self._icon, font=self._ifont, fill=fg, anchor="w"
            )
            x += iw
        self.create_text(
            x, self._h / 2, text=self._text, font=self._font, fill=fg, anchor="w"
        )


class GlowBar(tk.Canvas):
    """Track progress: rounded track, gradient-coloured fill and a glowing head."""

    def __init__(self, parent, height=18, bg=SURFACE):
        tk.Canvas.__init__(
            self, parent, height=height, bg=bg, highlightthickness=0, bd=0
        )
        self._h, self._frac, self._bg = height, 0.0, bg
        self.bind("<Configure>", lambda _e: self._draw())

    def set(self, frac: float):
        frac = max(0.0, min(1.0, frac))
        if abs(frac - self._frac) > 0.0004:
            self._frac = frac
            self._draw()

    def _draw(self):
        w, h = self.winfo_width(), self._h
        if w < 12:
            return
        self.delete("all")
        mid = h / 2
        self.create_polygon(
            round_rect_points(0, mid - 3, w, mid + 3, 3),
            smooth=True,
            fill="#232a48",
            outline="",
        )
        fx = self._frac * (w - 12) + 6
        if self._frac > 0:
            n = 18
            cols = gradient([PINK, VIOLET, CYAN], n)
            seg = max(fx / n, 1)
            for i in range(n):
                self.create_rectangle(
                    i * seg,
                    mid - 3,
                    min((i + 1) * seg + 1, fx),
                    mid + 3,
                    fill=cols[i],
                    outline="",
                )
            self.create_oval(
                fx - 11,
                mid - 11,
                fx + 11,
                mid + 11,
                fill=lerp_color(self._bg, CYAN, 0.22),
                outline="",
            )
            self.create_oval(
                fx - 6, mid - 6, fx + 6, mid + 6, fill="#ffffff", outline=CYAN, width=2
            )


class VolSlider(tk.Canvas):
    """Volume slider; command(v) fires when the knob is released, on_change(v) while dragging."""

    def __init__(self, parent, command=None, on_change=None, bg=SURFACE, height=26):
        tk.Canvas.__init__(
            self,
            parent,
            height=height,
            bg=bg,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self._h, self._v, self._cmd, self._chg, self.dragging = (
            height,
            50,
            command,
            on_change,
            False,
        )
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<ButtonPress-1>", self._move_start)
        self.bind("<B1-Motion>", self._move)
        self.bind("<ButtonRelease-1>", self._release)

    def get(self) -> int:
        return int(self._v)

    def set(self, v: float):
        v = max(0, min(100, v))
        if not self.dragging and int(v) != int(self._v):
            self._v = v
            self._draw()

    def _from_x(self, x):
        w = max(self.winfo_width(), 30)
        return max(0, min(100, (x - 10) / (w - 20) * 100))

    def _move_start(self, e):
        self.dragging = True
        self._move(e)

    def _move(self, e):
        self._v = self._from_x(e.x)
        self._draw()
        if self._chg:
            self._chg(int(self._v))

    def _release(self, e):
        self._v = self._from_x(e.x)
        self.dragging = False
        self._draw()
        if self._cmd:
            self._cmd(int(self._v))

    def _draw(self):
        w, h = self.winfo_width(), self._h
        if w < 30:
            return
        self.delete("all")
        mid, x = h / 2, 10 + self._v / 100 * (w - 20)
        self.create_polygon(
            round_rect_points(8, mid - 3, w - 8, mid + 3, 3),
            smooth=True,
            fill="#232a48",
            outline="",
        )
        if x > 12:
            self.create_polygon(
                round_rect_points(8, mid - 3, x, mid + 3, 3),
                smooth=True,
                fill=CYAN,
                outline="",
            )
        self.create_oval(
            x - 9,
            mid - 9,
            x + 9,
            mid + 9,
            fill=lerp_color(self["bg"], CYAN, 0.2),
            outline="",
        )
        self.create_oval(
            x - 6, mid - 6, x + 6, mid + 6, fill="#ffffff", outline=CYAN, width=2
        )


class App(tk.Tk):
    def __init__(self, engine):
        self._enable_dpi()
        super().__init__()
        self.e = engine
        self.k = max(
            1.0, self.winfo_fpixels("1i") / 96.0
        )  # display scaling: sizes below are for 96 dpi
        self.title("AutoDJ")
        self._set_icon()
        self.geometry(f"{self.px(1200)}x{self.px(780)}")
        self.minsize(self.px(1020), self.px(700))
        self.configure(bg=BG)
        self._labels: list[tuple] = []
        self._q_tracks: list = []  # the Track objects behind the queue list box, in display order
        self._drag = False
        self._seen = 0  # show whatever is already in the log
        self._q_cache = self._h_cache = None
        self._state = "idle"  # idle | playing | paused (drives the animations)
        self._level, self._spin, self._angle, self._t_prev = (
            0.05,
            0.0,
            0.0,
            time.monotonic(),
        )
        self._bar_items: list = []
        self._bars: list[float] = []
        self._bar_geo = (0, 1, 0, 1)
        self._vc = None
        self._tab = "queue"
        self._closing = False
        self._anim_err = False
        self._particles = make_particles(26, seed=1)
        self._confetti: list[
            tuple[float, dict, int]
        ] = []  # (launch_time, piece, item) still animating
        self._last_track_id: int | None = None
        self._border_glow = (
            0.0  # 0..1 window-border-glow intensity, pulses with playback
        )
        self._fonts()
        self._style()
        self._build()
        install_clipboard(self, lambda: self.e.lang)
        self.relabel()
        self.show_tab("queue")
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind_all("<space>", self._key_space)
        self.bind_all("<Control-Right>", lambda _e: self.e.skip())
        self.after(60, self._dark_titlebar)
        self.refresh()
        self._tick()

    # ---- environment -----------------------------------------------------
    @staticmethod
    def _enable_dpi():
        if os.name == "nt":
            try:
                import ctypes

                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(1)
                except Exception:
                    ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    def px(self, n: float) -> int:
        return round(n * self.k)

    def _dark_titlebar(self):
        if os.name != "nt":
            return
        try:
            import ctypes

            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            val = ctypes.c_int(1)
            for attr in (
                20,
                19,
            ):  # DWMWA_USE_IMMERSIVE_DARK_MODE (Win10 2004+/Win11, older builds use 19)
                if (
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd, attr, ctypes.byref(val), ctypes.sizeof(val)
                    )
                    == 0
                ):
                    break
        except Exception:
            pass

    def _set_icon(self):
        import sys
        from pathlib import Path

        base = Path(
            getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)
        )  # frozen exe unpacks app.ico here
        ico = base / "app.ico"
        if os.name == "nt" and ico.exists():
            try:
                self.iconbitmap(default=str(ico))
            except Exception:
                pass

    # ---- construction ----------------------------------------------------
    def _fonts(self):
        mk = lambda size, weight="normal", fam=FAMILY: tkfont.Font(
            root=self, family=fam, size=size, weight=weight
        )
        self.f_body, self.f_bold, self.f_small = mk(10), mk(10, "bold"), mk(9)
        self.f_list, self.f_title, self.f_brand = mk(11), mk(21, "bold"), mk(21, "bold")
        self.f_h2, self.f_icon = mk(11, "bold"), mk(11, "normal", "Segoe UI Symbol")
        self.f_big_icon = mk(13, "normal", "Segoe UI Symbol")

    def _style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure(
            "Vertical.TScrollbar",
            background=SURFACE2,
            troughcolor=SURFACE,
            bordercolor=SURFACE,
            arrowcolor=MUTED,
            lightcolor=SURFACE2,
            darkcolor=SURFACE2,
            relief="flat",
        )
        s.map("Vertical.TScrollbar", background=[("active", BORDER)])

    def _card(self, parent):
        return tk.Frame(
            parent,
            bg=SURFACE,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=BORDER,
        )

    def _lbl(self, parent, key, font=None, fg=MUTED, bg=SURFACE, **kw):
        w = tk.Label(parent, bg=bg, fg=fg, font=font or self.f_small, **kw)
        self._labels.append((w, key))
        return w

    def _btn(
        self, parent, key, cmd, kind="ghost", icon="", bg=SURFACE, height=38, minw=0
    ):
        w = PillButton(
            parent,
            command=cmd,
            kind=kind,
            icon=icon,
            font=self.f_bold,
            icon_font=self.f_icon,
            bg=bg,
            height=self.px(height),
            minw=self.px(minw),
        )
        self._labels.append((w, key))
        return w

    def _entry(self, parent):
        ent = tk.Entry(
            parent,
            bg=SURFACE2,
            fg=TEXT,
            insertbackground=CYAN,
            relief="flat",
            font=self.f_list,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=VIOLET,
            selectbackground=VIOLET,
            selectforeground="#ffffff",
            bd=0,
        )
        return ent

    def _listbox(self, parent):
        return tk.Listbox(
            parent,
            bg=SURFACE,
            fg=TEXT,
            selectbackground="#2a2160",
            selectforeground=TEXT,
            relief="flat",
            highlightthickness=0,
            activestyle="none",
            selectmode="extended",
            font=self.f_list,
            bd=0,
            exportselection=False,
        )

    def _build(self):
        px = self.px
        self._border = tk.Frame(
            self, bg=BG
        )  # a few px of this shows around `root`: the animated glow border
        self._border.pack(fill="both", expand=True)
        root = tk.Frame(self._border, bg=BG)
        root.pack(fill="both", expand=True, padx=px(3), pady=px(3))

        # header: logo, language pills, ON AIR light
        hdr = tk.Frame(root, bg=BG)
        hdr.pack(fill="x", padx=px(26), pady=(px(16), px(10)))
        logo = tk.Canvas(
            hdr, width=px(170), height=px(44), bg=BG, highlightthickness=0, bd=0
        )
        logo.pack(side="left")
        halo = logo.create_text(
            1,
            px(22) + 1,
            text="AUTODJ",
            font=self.f_brand,
            fill=lerp_color(PINK, BG, 0.4),
            anchor="w",
        )
        logo.create_text(
            0, px(22), text="AUTO", font=self.f_brand, fill=TEXT, anchor="w"
        )
        logo.create_text(
            self.f_brand.measure("AUTO") + 2,
            px(22),
            text="DJ",
            font=self.f_brand,
            fill=PINK,
            anchor="w",
        )
        self._logo_halo = halo
        tk.Label(
            hdr, text="CAMFROG  ·  ROOM MUSIC BOT", bg=BG, fg=MUTED, font=self.f_small
        ).pack(side="left", padx=(px(8), 0), pady=(px(8), 0))
        self.b_lang = {}
        for code in ("th", "en"):
            b = PillButton(
                hdr,
                text=code.upper(),
                command=lambda c=code: self.set_lang(c),
                kind="tab",
                font=self.f_bold,
                bg=BG,
                height=px(32),
                minw=px(52),
                padx=px(10),
            )
            b.pack(side="right", padx=(px(6), 0))
            self.b_lang[code] = b
        self.led = tk.Canvas(
            hdr, width=px(18), height=px(18), bg=BG, highlightthickness=0, bd=0
        )
        self._led_id = self.led.create_oval(
            px(3), px(3), px(15), px(15), fill="#3a3f5c", outline=""
        )
        self.led.pack(side="right", padx=(0, px(6)))
        self.v_onair = self._lbl(hdr, "g_on_air", font=self.f_bold, bg=BG)
        self.v_onair.pack(side="right", padx=(px(18), px(2)))

        # animated gradient line under the header
        self.line = tk.Canvas(root, height=3, bg=BG, highlightthickness=0, bd=0)
        self.line.pack(fill="x")
        self._shimmer = None
        self.line.bind("<Configure>", self._layout_line)

        # warning when mpv cannot be found (nothing could play)
        avail = getattr(self.e.player, "available", None)
        if callable(avail) and not avail():
            ban = tk.Label(
                root,
                bg="#3a1424",
                fg="#ffb3c6",
                font=self.f_body,
                anchor="w",
                padx=px(26),
                pady=px(8),
            )
            self._labels.append((ban, "g_mpv_missing"))
            ban.pack(fill="x")

        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True, padx=px(26), pady=(px(18), px(22)))
        body.columnconfigure(0, weight=5, minsize=px(520))
        body.columnconfigure(1, weight=4, minsize=px(380))
        body.rowconfigure(0, weight=1)
        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, px(20)))
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")

        # ---- now-playing card
        card = self._card(left)
        card.pack(fill="x")
        self.stage = tk.Canvas(
            card, height=px(230), bg=SURFACE, highlightthickness=0, bd=0
        )
        self.stage.pack(fill="x")
        self.stage.bind("<Configure>", self._layout_stage)
        info = tk.Frame(card, bg=SURFACE)
        info.pack(fill="x", padx=px(22), pady=(px(10), px(18)))
        self.v_title = tk.Label(
            info,
            bg=SURFACE,
            fg=TEXT,
            font=self.f_title,
            anchor="w",
            justify="left",
            wraplength=px(560),
        )
        self.v_title.pack(fill="x")
        self.v_sub = tk.Label(info, bg=SURFACE, fg=CYAN, font=self.f_body, anchor="w")
        self.v_sub.pack(fill="x", pady=(px(2), px(10)))
        self.bar = GlowBar(info, height=px(22), bg=SURFACE)
        self.bar.pack(fill="x")
        self.v_time = tk.Label(
            info, bg=SURFACE, fg=MUTED, font=self.f_small, anchor="w"
        )
        self.v_time.pack(fill="x", pady=(0, px(10)))
        ctl = tk.Frame(info, bg=SURFACE)
        ctl.pack(fill="x")
        self.b_pause = PillButton(
            ctl,
            command=self.toggle_pause,
            kind="primary",
            icon="❚❚",
            font=self.f_bold,
            icon_font=self.f_big_icon,
            bg=SURFACE,
            height=px(44),
            minw=px(150),
            padx=px(20),
        )
        self.b_pause.pack(side="left")
        skip = self._btn(ctl, "g_skip", self.e.skip, icon="▶▶", height=44, minw=110)
        skip.pack(side="left", padx=(px(10), 0))
        discover = self._btn(
            ctl, "g_discover", self.do_discover, icon="🔍", height=44, minw=130
        )
        discover.pack(side="left", padx=(px(10), 0))
        check = self._btn(
            ctl, "g_check", self.do_check, icon="✓", height=44, minw=110
        )
        check.pack(side="left", padx=(px(10), 0))
        self.v_volpct = tk.Label(
            ctl, bg=SURFACE, fg=TEXT, font=self.f_bold, width=5, anchor="e"
        )
        self.v_volpct.pack(side="right")
        self.vol = VolSlider(
            ctl,
            command=self._vol_release,
            on_change=self._vol_live,
            bg=SURFACE,
            height=px(28),
        )
        self.vol.pack(side="right", fill="x", expand=True, padx=(px(24), px(6)))
        self._lbl(ctl, "g_vol", bg=SURFACE).pack(side="right", padx=(px(18), 0))
        self.v_next = tk.Label(
            info,
            bg=SURFACE,
            fg=MUTED,
            font=self.f_small,
            anchor="w",
            justify="left",
            wraplength=px(560),
        )
        self.v_next.pack(fill="x", pady=(px(12), 0))
        card.bind(
            "<Configure>",
            lambda e: [
                w.configure(wraplength=max(200, e.width - px(48)))
                for w in (self.v_title, self.v_next)
            ],
        )

        # ---- add row
        add = tk.Frame(left, bg=BG)
        add.pack(fill="x", pady=(px(18), 0))
        self.ent_add = self._entry(add)
        self.ent_add.pack(
            side="left", fill="x", expand=True, ipady=px(9), padx=(0, px(10))
        )
        self.ent_add.bind("<Return>", lambda _e: self.add())
        self._btn(add, "g_add", self.add, "primary", icon="＋", bg=BG, height=40).pack(
            side="left"
        )
        self._btn(add, "g_folder", self.load_folder, bg=BG, height=40).pack(
            side="left", padx=(px(8), 0)
        )
        self._btn(add, "g_file", self.add_files, bg=BG, height=40).pack(
            side="left", padx=(px(8), 0)
        )
        self.v_hint = tk.Label(left, bg=BG, fg=MUTED, font=self.f_small, anchor="w")
        self.v_hint.pack(fill="x", pady=(px(6), 0))
        opts = tk.Frame(left, bg=BG)
        opts.pack(fill="x", pady=(px(12), 0))
        self.c_shuffle = self._btn(
            opts, "g_shuffle", self.on_shuffle, "chip", icon="⇄", bg=BG, height=34
        )
        self.c_shuffle.pack(side="left")
        self.c_repeat = self._btn(
            opts, "g_repeat", self.on_repeat, "chip", icon="↻", bg=BG, height=34
        )
        self.c_repeat.pack(side="left", padx=(px(8), 0))

        # ---- tabbed panel: queue / history / chat
        panel = self._card(right)
        panel.pack(fill="both", expand=True)
        bar = tk.Frame(panel, bg=SURFACE)
        bar.pack(fill="x", padx=px(14), pady=(px(14), px(8)))
        self.tabs = {}
        for key, lab in (
            ("queue", "g_queue"),
            ("history", "g_history"),
            ("chat", "g_chat"),
            ("settings", "g_settings"),
        ):
            b = self._btn(bar, lab, lambda k=key: self.show_tab(k), "tab", height=34)
            b.pack(side="left", padx=(0, px(6)))
            self.tabs[key] = b
        pages = tk.Frame(panel, bg=SURFACE)
        pages.pack(fill="both", expand=True, padx=px(14), pady=(0, px(14)))
        self.pages = {
            k: tk.Frame(pages, bg=SURFACE) for k in ("queue", "history", "chat", "settings")
        }

        qp = self.pages["queue"]
        qb = tk.Frame(qp, bg=SURFACE)
        qb.pack(side="bottom", fill="x", pady=(px(10), 0))
        self._btn(qb, "g_remove", self.remove_selected, "danger", height=34).pack(
            side="left"
        )
        self._btn(qb, "g_clear", self.e.queue.clear, height=34).pack(
            side="left", padx=(px(8), 0)
        )
        sb = ttk.Scrollbar(qp, orient="vertical")
        sb.pack(side="right", fill="y")
        self.lb = self._listbox(qp)
        self.lb.pack(side="left", fill="both", expand=True)
        self.lb.configure(yscrollcommand=sb.set)
        sb.configure(command=self.lb.yview)

        hp = self.pages["history"]
        hb = ttk.Scrollbar(hp, orient="vertical")
        hb.pack(side="right", fill="y")
        self.hist = self._listbox(hp)
        self.hist.pack(side="left", fill="both", expand=True)
        self.hist.configure(yscrollcommand=hb.set)
        hb.configure(command=self.hist.yview)

        cp = self.pages["chat"]
        sr = tk.Frame(cp, bg=SURFACE)
        sr.pack(side="bottom", fill="x", pady=(px(10), 0))
        self.ent_say = self._entry(sr)
        self.ent_say.pack(
            side="left", fill="x", expand=True, ipady=px(7), padx=(0, px(8))
        )
        self.ent_say.bind("<Return>", lambda _e: self.say())
        self._btn(sr, "g_say", self.say, "primary", height=34).pack(side="left")
        self._btn(sr, "g_speak", self.speak, height=34).pack(
            side="left", padx=(px(8), 0)
        )
        cs = ttk.Scrollbar(cp, orient="vertical")
        cs.pack(side="right", fill="y")
        self.chat = tk.Text(
            cp,
            bg=SURFACE,
            fg=TEXT,
            wrap="word",
            state="disabled",
            relief="flat",
            highlightthickness=0,
            padx=px(8),
            pady=px(6),
            font=self.f_body,
            insertbackground=CYAN,
            selectbackground=VIOLET,
            bd=0,
        )
        self.chat.pack(side="left", fill="both", expand=True)
        self.chat.configure(yscrollcommand=cs.set)
        cs.configure(command=self.chat.yview)
        self.chat.tag_configure("bot", foreground=CYAN)
        self.chat.tag_configure("who", foreground="#b79cff", font=self.f_bold)

        sp = self.pages["settings"]
        sp.columnconfigure(0, weight=1)
        sp_inner = tk.Frame(sp, bg=SURFACE)
        sp_inner.pack(fill="both", expand=True, padx=px(14), pady=px(14))
        sp_inner.columnconfigure(0, weight=1)

        row = 0

        def _setting_row(label_key, widget, note_key=None, padx=(px(14), px(14))):
            nonlocal row
            lf = tk.Frame(sp_inner, bg=SURFACE)
            lf.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(px(6), px(2)), padx=padx)
            lbl = tk.Label(lf, bg=SURFACE, fg=TEXT, font=self.f_body, anchor="w")
            lbl.pack(in_=lf, side="left")
            self._labels.append((lbl, label_key))
            widget.pack(in_=lf, side="right", fill="x", expand=True, padx=(px(10), 0))
            if note_key:
                note = tk.Label(
                    sp_inner, bg=SURFACE, fg=MUTED, font=self.f_small, anchor="w"
                )
                note.grid(row=row + 1, column=0, columnspan=2, sticky="w", padx=padx)
                self._labels.append((note, note_key))
                row += 2
            else:
                row += 1
            return widget

        # Language (handled by header pills, shown for reference)
        tk.Label(
            sp_inner,
            bg=SURFACE,
            fg=MUTED,
            font=self.f_bold,
            anchor="w",
            text=self.e.t("g_settings_lang") + " (use header pills)",
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(px(10), px(2)), padx=(px(14), px(14)))
        row += 1

        # mpv_path
        self.s_mpv_path = self._entry(sp_inner)
        self.s_mpv_path.insert(0, self.e.cfg.mpv_path)
        _setting_row("g_settings_mpv_path", self.s_mpv_path, "g_settings_ytdlp_path")

        # ytdlp_path
        self.s_ytdlp_path = self._entry(sp_inner)
        self.s_ytdlp_path.insert(0, self.e.cfg.ytdlp_path)
        _setting_row("g_settings_ytdlp_path", self.s_ytdlp_path, "g_settings_audio_device")

        # audio_device
        self.s_audio_device = self._entry(sp_inner)
        self.s_audio_device.insert(0, self.e.cfg.audio_device)
        _setting_row("g_settings_audio_device", self.s_audio_device, "g_settings_bot_nick")

        # bot_nick
        self.s_bot_nick = self._entry(sp_inner)
        self.s_bot_nick.insert(0, self.e.cfg.bot_nick)
        _setting_row("g_settings_bot_nick", self.s_bot_nick, "g_settings_prefix")

        # prefix
        self.s_prefix = self._entry(sp_inner)
        self.s_prefix.insert(0, self.e.cfg.prefix)
        _setting_row("g_settings_prefix", self.s_prefix, "g_settings_admins")

        # admins
        self.s_admins = self._entry(sp_inner)
        self.s_admins.insert(0, ", ".join(self.e.cfg.admins))
        _setting_row("g_settings_admins", self.s_admins, "g_settings_blocked_users")

        # blocked_users
        self.s_blocked_users = self._entry(sp_inner)
        self.s_blocked_users.insert(0, ", ".join(self.e.cfg.blocked_users))
        _setting_row("g_settings_blocked_users", self.s_blocked_users, "g_settings_room")

        # room
        self.s_room = self._entry(sp_inner)
        self.s_room.insert(0, self.e.cfg.room)
        _setting_row("g_settings_room", self.s_room, "g_settings_join_uri")

        # join_uri_template
        self.s_join_uri = self._entry(sp_inner)
        self.s_join_uri.insert(0, self.e.cfg.join_uri_template)
        _setting_row("g_settings_join_uri", self.s_join_uri, "g_settings_music_dirs")

        # music_dirs
        self.s_music_dirs = self._entry(sp_inner)
        self.s_music_dirs.insert(0, ", ".join(self.e.cfg.music_dirs))
        _setting_row("g_settings_music_dirs", self.s_music_dirs, "g_settings_autoplay_sources")

        # autoplay_sources
        self.s_autoplay_sources = self._entry(sp_inner)
        self.s_autoplay_sources.insert(0, ", ".join(self.e.cfg.autoplay_sources))
        _setting_row("g_settings_autoplay_sources", self.s_autoplay_sources, "g_settings_volume")

        # volume
        self.s_volume = self._entry(sp_inner)
        self.s_volume.insert(0, str(self.e.cfg.volume))
        _setting_row("g_settings_volume", self.s_volume, "g_settings_max_queue")

        # max_queue
        self.s_max_queue = self._entry(sp_inner)
        self.s_max_queue.insert(0, str(self.e.cfg.max_queue))
        _setting_row("g_settings_max_queue", self.s_max_queue, "g_settings_max_duration")

        # max_duration
        self.s_max_duration = self._entry(sp_inner)
        self.s_max_duration.insert(0, str(self.e.cfg.max_duration))
        _setting_row("g_settings_max_duration", self.s_max_duration, "g_settings_cooldown")

        # cooldown
        self.s_cooldown = self._entry(sp_inner)
        self.s_cooldown.insert(0, str(self.e.cfg.cooldown))
        _setting_row("g_settings_cooldown", self.s_cooldown, "g_settings_send_interval")

        # send_interval
        self.s_send_interval = self._entry(sp_inner)
        self.s_send_interval.insert(0, str(self.e.cfg.send_interval))
        _setting_row("g_settings_send_interval", self.s_send_interval, "g_settings_poll_interval")

        # poll_interval
        self.s_poll_interval = self._entry(sp_inner)
        self.s_poll_interval.insert(0, str(self.e.cfg.poll_interval))
        _setting_row("g_settings_poll_interval", self.s_poll_interval, "g_settings_search_limit")

        # search_limit
        self.s_search_limit = self._entry(sp_inner)
        self.s_search_limit.insert(0, str(self.e.cfg.search_limit))
        _setting_row("g_settings_search_limit", self.s_search_limit, "g_settings_mpv_timeout")

        # mpv_timeout
        self.s_mpv_timeout = self._entry(sp_inner)
        self.s_mpv_timeout.insert(0, str(self.e.cfg.mpv_timeout))
        _setting_row("g_settings_mpv_timeout", self.s_mpv_timeout, "g_settings_tts_voice")

        # tts_voice
        self.s_tts_voice = self._entry(sp_inner)
        self.s_tts_voice.insert(0, self.e.cfg.tts_voice)
        _setting_row("g_settings_tts_voice", self.s_tts_voice, "g_settings_tts_rate")

        # tts_rate
        self.s_tts_rate = self._entry(sp_inner)
        self.s_tts_rate.insert(0, str(self.e.cfg.tts_rate))
        _setting_row("g_settings_tts_rate", self.s_tts_rate, "g_settings_tts_duck")

        # tts_duck
        self.s_tts_duck = self._entry(sp_inner)
        self.s_tts_duck.insert(0, str(self.e.cfg.tts_duck))
        _setting_row("g_settings_tts_duck", self.s_tts_duck, "g_settings_auto_discover")

        # auto_discover toggle
        self.s_auto_discover = self.e.cfg.auto_discover
        cb_auto_discover = self._btn(
            sp_inner,
            "",
            lambda: self._toggle_bool("s_auto_discover", cb_auto_discover),
            "chip",
            icon="✓" if self.e.cfg.auto_discover else "",
            bg=SURFACE,
            height=34,
            minw=200,
        )
        cb_auto_discover.set_active(self.e.cfg.auto_discover)
        cb_auto_discover.grid(row=row, column=0, columnspan=2, sticky="w", pady=(px(6), px(2)), padx=(px(14), px(14)))
        row += 1

        # auto_launch toggle
        self.s_auto_launch = self.e.cfg.auto_launch
        cb_auto_launch = self._btn(
            sp_inner,
            "",
            lambda: self._toggle_bool("s_auto_launch", cb_auto_launch),
            "chip",
            icon="✓" if self.e.cfg.auto_launch else "",
            bg=SURFACE,
            height=34,
            minw=200,
        )
        cb_auto_launch.set_active(self.e.cfg.auto_launch)
        cb_auto_launch.grid(row=row, column=0, columnspan=2, sticky="w", pady=(px(6), px(2)), padx=(px(14), px(14)))
        row += 1

        # camfrog_exe
        self.s_camfrog_exe = self._entry(sp_inner)
        self.s_camfrog_exe.insert(0, self.e.cfg.camfrog_exe)
        _setting_row("g_settings_camfrog_exe", self.s_camfrog_exe, "g_settings_client_title_re")

        # client_title_re
        self.s_client_title_re = self._entry(sp_inner)
        self.s_client_title_re.insert(0, self.e.cfg.client_title_re)
        _setting_row("g_settings_client_title_re", self.s_client_title_re, "g_settings_launch_timeout")

        # launch_timeout
        self.s_launch_timeout = self._entry(sp_inner)
        self.s_launch_timeout.insert(0, str(self.e.cfg.launch_timeout))
        _setting_row("g_settings_launch_timeout", self.s_launch_timeout, "g_settings_line_regex")

        # line_regex
        self.s_line_regex = self._entry(sp_inner)
        self.s_line_regex.insert(0, self.e.cfg.line_regex)
        _setting_row("g_settings_line_regex", self.s_line_regex, "g_settings_log_file")

        # log_file
        self.s_log_file = self._entry(sp_inner)
        self.s_log_file.insert(0, self.e.cfg.log_file)
        _setting_row("g_settings_log_file", self.s_log_file, None)

        # Save button
        save_btn = self._btn(
            sp_inner,
            "g_settings_save",
            self.save_settings,
            "primary",
            icon="✓",
            bg=SURFACE,
            height=40,
            minw=120,
        )
        save_btn.grid(row=row, column=0, columnspan=2, pady=(px(18), px(14)), padx=(px(14), px(14)))
        row += 1

    # ---- animated scenery ---------------------------------------------------
    def _layout_line(self, _e=None):
        w = self.line.winfo_width()
        if w < 10:
            return
        self.line.delete("all")
        n = 90
        cols = gradient([PINK, VIOLET, CYAN, VIOLET, PINK], n)
        seg = w / n
        for i, c in enumerate(cols):
            self.line.create_rectangle(
                i * seg, 0, (i + 1) * seg + 1, 3, fill=c, outline=""
            )
        self._shimmer = self.line.create_rectangle(
            -200, 0, -80, 3, fill="#ffffff", outline=""
        )

    def _layout_stage(self, _e=None):
        c, px = self.stage, self.px
        w, h = c.winfo_width(), c.winfo_height()
        if w < 60 or h < 60:
            return
        c.delete("all")
        self._stage_wh = (w, h)
        if not hasattr(self, "_stars"):
            rnd, x = [], 1
            for _ in range(60):
                x = (x * 9301 + 49297) % 233280
                rnd.append(x / 233280)
            self._stars = [
                (rnd[i * 2 % 60], rnd[(i * 2 + 1) % 60], 0.4 + rnd[i % 60] * 1.3)
                for i in range(30)
            ]
        n = len(AURORA)
        strip = h / n * 1.8
        self._aurora_items = [
            c.create_rectangle(
                0, i * h / n, w, i * h / n + strip, fill=AURORA[i], outline=""
            )
            for i in range(n)
        ]
        self._star_items = [
            c.create_oval(
                sx * w,
                sy * h * 0.7,
                sx * w + sr * 2,
                sy * h * 0.7 + sr * 2,
                fill="#ffffff",
                outline="",
                stipple="gray25",
            )
            for sx, sy, sr in self._stars
        ]
        cx, cy, r = h * 0.56, h / 2, min(h * 0.38, px(92))
        self._glow = [
            c.create_oval(
                cx - r - d,
                cy - r - d,
                cx + r + d,
                cy + r + d,
                fill=lerp_color("#0d1021", PINK, 0.05 + 0.03 * i),
                outline="",
            )
            for i, d in enumerate((px(44), px(28), px(14)))
        ]
        c.create_oval(
            cx - r, cy - r, cx + r, cy + r, fill="#07080f", outline="#2b3156", width=2
        )
        for f in (0.92, 0.82, 0.72, 0.62, 0.52):
            c.create_oval(
                cx - r * f, cy - r * f, cx + r * f, cy + r * f, outline="#171a2e"
            )
        rs = r * 0.94
        self._sheen = [
            c.create_arc(
                cx - rs,
                cy - rs,
                cx + rs,
                cy + rs,
                start=a,
                extent=34,
                style="arc",
                outline="#566099",
                width=3,
            )
            for a in (20, 200)
        ]
        lab = r * 0.36
        c.create_oval(
            cx - lab,
            cy - lab,
            cx + lab,
            cy + lab,
            fill=PINK,
            outline=lerp_color(PINK, "#ffffff", 0.4),
            width=2,
        )
        c.create_oval(
            cx - lab * 0.55,
            cy - lab * 0.55,
            cx + lab * 0.55,
            cy + lab * 0.55,
            fill=VIOLET,
            outline="",
        )
        self._needle = c.create_line(
            cx, cy, cx + lab * 0.8, cy, fill="#ffffff", width=2
        )
        c.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill="#0a0c14", outline="")
        self._vc = (cx, cy, r, lab)
        self._particle_items = [
            c.create_oval(0, 0, 1, 1, fill=col, outline="")
            for col in gradient([CYAN, VIOLET, PINK, "#ffffff"], len(self._particles))
        ]
        self._confetti_items: list[int] = []
        x0, x1 = cx + r + px(52), w - px(26)
        self._bar_items, self._bars = [], []
        if x1 - x0 > px(90):
            nb = max(12, min(48, int((x1 - x0) / px(14))))
            bw, base = (x1 - x0) / nb, h - px(24)
            cols = gradient([CYAN, VIOLET, PINK], nb)
            self._bar_items = [
                c.create_rectangle(
                    x0 + i * bw + 1,
                    base - 2,
                    x0 + (i + 1) * bw - 2,
                    base,
                    fill=cols[i],
                    outline="",
                )
                for i in range(nb)
            ]
            self._bars = [0.03] * nb
            self._bar_geo = (x0, bw, base, h - px(66))
            c.create_line(x0, base + 5, x1, base + 5, fill=BORDER)
        self._stage_tag = c.create_text(
            px(20),
            px(14),
            text=self.e.t("g_now").upper(),
            anchor="nw",
            fill=MUTED,
            font=self.f_small,
        )

    def _tick(self):
        try:
            self._frame()
        except Exception:
            if not self._anim_err:  # log once, keep animating
                self._anim_err = True
                log.exception("GUI animation frame failed")
        finally:
            if not self._closing:
                self._anim = self.after(
                    250 if self.state() == "iconic" else FPS_MS, self._tick
                )

    def _frame(self):
        t = time.monotonic()
        dt, self._t_prev = min(t - self._t_prev, 0.2), t
        st = self._state
        c = self.stage
        if getattr(self, "_aurora_items", None):
            w, h = getattr(self, "_stage_wh", (0, 0))
            n = len(self._aurora_items)
            strip = h / n * 1.8 if n else 0
            for i, item in enumerate(self._aurora_items):
                off = aurora_offset(t, i, n) * h * 0.1
                y0 = i * h / n - off
                c.coords(item, 0, y0, w, y0 + strip)
            for i, (item, (sx, sy, sr)) in enumerate(
                zip(self._star_items, self._stars)
            ):
                a = 0.4 + 0.6 * pulse(t * 0.6 + i * 0.9, 2.3)
                c.itemconfigure(
                    item,
                    stipple="gray75"
                    if a > 0.7
                    else ("gray50" if a > 0.4 else "gray25"),
                )
        if self._vc and getattr(self, "_particle_items", None):
            cx, cy, r, _lab = self._vc
            for item, p in zip(self._particle_items, self._particles):
                x, y, alpha = particle_pos(p, t, cx, cy, r + self.px(70))
                s = p["size"] * (0.6 + 0.7 * alpha) * (1.0 if st == "playing" else 0.5)
                c.coords(item, x - s, y - s, x + s, y + s)
                c.itemconfigure(
                    item,
                    stipple="gray75"
                    if alpha > 0.75
                    else ("gray50" if alpha > 0.45 else "gray25"),
                )
        self._run_confetti(t)
        glow_target = 0.75 + 0.25 * pulse(t, 1.5) if st == "playing" else 0.0
        self._border_glow = ease(self._border_glow, glow_target, 0.12, 0.05)
        self._border.configure(bg=lerp_color(BG, PINK, 0.55 * self._border_glow))
        target = (
            1.0
            if st == "playing"
            else (0.10 if st == "paused" else 0.05 + 0.04 * pulse(t, 3.0))
        )
        self._level = ease(self._level, target, 0.15, 0.08)
        c = self.stage
        if self._bar_items:
            tgt = bar_heights(t, len(self._bar_items), self._level)
            x0, bw, base, maxh = self._bar_geo
            for i, item in enumerate(self._bar_items):
                self._bars[i] = ease(self._bars[i], tgt[i])
                c.coords(
                    item,
                    x0 + i * bw + 1,
                    base - max(2.0, self._bars[i] * maxh),
                    x0 + (i + 1) * bw - 2,
                    base,
                )
        if self._vc:
            cx, cy, _r, lab = self._vc
            self._spin = ease(self._spin, 1.0 if st == "playing" else 0.0, 0.08, 0.04)
            self._angle = (
                self._angle + self._spin * dt * 200.0
            ) % 360.0  # 33⅓ rpm = 200 deg/s
            c.itemconfigure(self._sheen[0], start=self._angle)
            c.itemconfigure(self._sheen[1], start=(self._angle + 180) % 360)
            a = math.radians(self._angle)
            c.coords(
                self._needle,
                cx,
                cy,
                cx + lab * 0.8 * math.cos(a),
                cy - lab * 0.8 * math.sin(a),
            )
            for i, ring in enumerate(self._glow):
                c.itemconfigure(
                    ring,
                    fill=lerp_color(
                        "#0d1021",
                        PINK,
                        (0.04 + 0.03 * i)
                        + 0.10 * self._level * pulse(t, 1.8) * (i + 1) / 3,
                    ),
                )
        if st == "playing" and self._cur_dur:
            self.bar.set(self.e.position() / self._cur_dur)
        self.led.itemconfigure(
            self._led_id,
            fill=lerp_color("#4a1f2c", RED, pulse(t, 1.4))
            if st == "playing"
            else "#3a3f5c",
        )
        if self._shimmer is not None and self.line.winfo_width() > 10:
            x = (t * 220) % (self.line.winfo_width() + 400) - 200
            self.line.coords(self._shimmer, x, 0, x + 110, 3)

    # ---- actions -------------------------------------------------------------
    def show_tab(self, name: str):
        self._tab = name
        for k, page in self.pages.items():
            page.pack_forget()
        self.pages[name].pack(fill="both", expand=True)
        for k, b in self.tabs.items():
            b.set_active(k == name)

    def set_lang(self, code: str):
        self.e.lang = code
        self.relabel()

    _cur_dur = 0

    def relabel(self):
        for w, k in self._labels:
            if k:  # skip empty keys (e.g., toggle buttons with dynamic text)
                w.configure(text=self.e.t(k))
        self.v_hint.configure(text=self.e.t("g_add_hint"))
        for code, b in self.b_lang.items():
            b.set_active(code == self.e.lang)
        self._sync_pause()
        if getattr(self, "_stage_tag", None) is not None:
            self.stage.itemconfigure(self._stage_tag, text=self.e.t("g_now").upper())
        self._q_cache = self._h_cache = None

    def _sync_pause(self):
        paused = bool(self.e.paused)
        self.b_pause.configure(text=self.e.t("g_resume" if paused else "g_pause"))
        self.b_pause.set_icon("▶" if paused else "❚❚")

    def toggle_pause(self):
        self.e.resume() if self.e.paused else self.e.pause()

    def _launch_confetti(self):
        if not self._vc:
            return
        pieces = confetti_burst(22, seed=int(time.monotonic() * 1000) % 10_000)
        cols = gradient([PINK, VIOLET, CYAN, GREEN, "#ffffff"], len(pieces))
        now = time.monotonic()
        for piece, col in zip(pieces, cols):
            item = self.stage.create_oval(0, 0, 1, 1, fill=col, outline="")
            self._confetti.append((now, piece, item))

    def _run_confetti(self, t: float):
        if not self._confetti or not self._vc:
            return
        cx, cy, _r, _lab = self._vc
        keep = []
        for launch, piece, item in self._confetti:
            age = t - launch
            if age >= 1.4:
                self.stage.delete(item)
                continue
            x, y, _rot, alpha = confetti_pos(piece, age, cx, cy)
            s = piece["size"] * (0.5 + 0.5 * alpha)
            self.stage.coords(item, x - s, y - s, x + s, y + s)
            self.stage.itemconfigure(
                item,
                stipple="gray75"
                if alpha > 0.7
                else ("gray50" if alpha > 0.35 else "gray25"),
            )
            keep.append((launch, piece, item))
        self._confetti = keep

    def _key_space(self, _e):
        try:
            typing = isinstance(self.focus_get(), (tk.Entry, tk.Text, ttk.Entry))
        except KeyError:
            typing = False
        if not typing:
            self.toggle_pause()
            return "break"

    def _vol_live(self, v):
        self.v_volpct.configure(text=f"{v}%")

    def _vol_release(self, v):
        self.e.set_volume(v)

    def add(self):
        text = self.ent_add.get().strip()
        if text:
            self.e.request(text)
            self.ent_add.delete(0, "end")

    def add_files(self):
        ext = " ".join(f"*{x}" for x in sorted(MEDIA))
        try:
            files = filedialog.askopenfilenames(
                filetypes=[("Media", ext), ("All", "*.*")]
            )
        except Exception:
            log.exception("file dialog failed")
            return
        for f in files:
            self.e.request(f)

    def load_folder(self):
        try:
            d = filedialog.askdirectory()
        except Exception:
            log.exception("folder dialog failed")
            return
        if d:
            self.e.load_async(d)

    def remove_selected(self):
        # by object, not by position: the queue may have changed since the list box was last refreshed
        for i in self.lb.curselection():
            if i < len(self._q_tracks):
                self.e.queue.remove_track(self._q_tracks[i])

    def on_shuffle(self):
        self.e.queue.set_shuffle(not self.e.queue.shuffle)

    def on_repeat(self):
        self.e.queue.repeat = "off" if self.e.queue.repeat == "one" else "one"

    def say(self):
        text = self.ent_say.get().strip()
        if text:
            self.e.say(text)
            self.ent_say.delete(0, "end")

    def speak(self):
        text = self.ent_say.get().strip()
        if text:
            self.e.speak(text)
            self.ent_say.delete(0, "end")

    def do_discover(self):
        """Run auto-discovery to find the Camfrog room window and chat controls."""
        import subprocess, sys
        try:
            subprocess.run(
                [sys.executable, "-m", "camfrog_autodj", "--discover", "-c", self.e.cfg_path if hasattr(self.e, "cfg_path") else "config.toml"],
                check=False,
            )
        except Exception:
            log.exception("discover failed")

    def do_check(self):
        """Run setup diagnostic: mpv, yt-dlp, folders, Camfrog window."""
        import subprocess, sys
        try:
            subprocess.run(
                [sys.executable, "-m", "camfrog_autodj", "--check", "-c", self.e.cfg_path if hasattr(self.e, "cfg_path") else "config.toml"],
                check=False,
            )
        except Exception:
            log.exception("check failed")

    def _toggle_bool(self, attr: str, btn: "PillButton"):
        """Toggle a boolean setting stored as a plain Python attribute."""
        setattr(self, attr, not getattr(self, attr))
        btn.set_active(getattr(self, attr))
        btn.set_icon("✓" if getattr(self, attr) else "")

    def save_settings(self):
        """Save settings from the settings tab back to config.toml."""
        try:
            cfg = self.e.cfg

            # String fields
            cfg.mpv_path = self.s_mpv_path.get().strip()
            cfg.ytdlp_path = self.s_ytdlp_path.get().strip()
            cfg.audio_device = self.s_audio_device.get().strip()
            cfg.bot_nick = self.s_bot_nick.get().strip()
            cfg.prefix = self.s_prefix.get().strip()
            cfg.room = self.s_room.get().strip()
            cfg.join_uri_template = self.s_join_uri.get().strip()
            cfg.camfrog_exe = self.s_camfrog_exe.get().strip()
            cfg.client_title_re = self.s_client_title_re.get().strip()
            cfg.line_regex = self.s_line_regex.get().strip()
            cfg.log_file = self.s_log_file.get().strip()

            # List fields
            cfg.admins = [a.strip() for a in self.s_admins.get().split(",") if a.strip()]
            cfg.blocked_users = [a.strip() for a in self.s_blocked_users.get().split(",") if a.strip()]
            cfg.music_dirs = [a.strip() for a in self.s_music_dirs.get().split(",") if a.strip()]
            cfg.autoplay_sources = [a.strip() for a in self.s_autoplay_sources.get().split(",") if a.strip()]

            # Int fields
            cfg.volume = int(self.s_volume.get())
            cfg.max_queue = int(self.s_max_queue.get())
            cfg.max_duration = int(self.s_max_duration.get())
            cfg.search_limit = int(self.s_search_limit.get())
            cfg.mpv_timeout = float(self.s_mpv_timeout.get())
            cfg.tts_rate = int(self.s_tts_rate.get())
            cfg.tts_duck = int(self.s_tts_duck.get())
            cfg.launch_timeout = int(self.s_launch_timeout.get())

            # Float fields
            cfg.cooldown = float(self.s_cooldown.get())
            cfg.send_interval = float(self.s_send_interval.get())
            cfg.poll_interval = float(self.s_poll_interval.get())

            # Bool fields
            cfg.auto_discover = self.s_auto_discover
            cfg.auto_launch = self.s_auto_launch

            # TTS voice
            cfg.tts_voice = self.s_tts_voice.get().strip()

            # Validate prefix not empty
            if not cfg.prefix.strip():
                raise ValueError("prefix must not be empty")

            # Validate regexes
            import re
            re.compile(cfg.line_regex)
            re.compile(cfg.client_title_re)

            # Write to config.toml using tomllib-compatible format
            import tomllib
            from pathlib import Path

            cfg_path = self.e.cfg_path if hasattr(self.e, "cfg_path") else "config.toml"
            p = Path(cfg_path)

            # Build TOML text manually preserving comments is complex, so we write a clean version
            lines = []
            lines.append(f'bot_nick = "{cfg.bot_nick}"')
            lines.append(f'admins = {cfg.admins!r}')
            lines.append(f'prefix = "{cfg.prefix}"')
            lines.append(f'lang = "{cfg.lang}"')
            lines.append("")
            lines.append(f'chat_reader = "{cfg.chat_reader}"')
            lines.append(f'chat_sender = "{cfg.chat_sender}"')
            lines.append(f'window_title_re = "{cfg.window_title_re}"')
            lines.append(f'process_re = "{cfg.process_re}"')
            lines.append(f'window_exclude_re = "{cfg.window_exclude_re}"')
            lines.append(f'window_index = {cfg.window_index}')
            lines.append(f'auto_discover = {str(cfg.auto_discover).lower()}')
            lines.append(f'view_kind = "{cfg.view_kind}"')
            lines.append(f'send_mode = "{cfg.send_mode}"')
            lines.append(f'send_verify = {str(cfg.send_verify).lower()}')
            lines.append(f'web_strict_body = {str(cfg.web_strict_body).lower()}')
            lines.append(f'view_type = "{cfg.view_type}"')
            lines.append(f'view_index = {cfg.view_index}')
            lines.append(f'input_type = "{cfg.input_type}"')
            lines.append(f'input_index = {cfg.input_index}')
            lines.append("")
            lines.append(f'mpv_path = "{cfg.mpv_path}"')
            lines.append(f'audio_device = "{cfg.audio_device}"')
            lines.append(f'volume = {cfg.volume}')
            lines.append(f'music_dirs = {cfg.music_dirs!r}')
            lines.append(f'autoplay_sources = {cfg.autoplay_sources!r}')
            lines.append(f'shuffle = {str(cfg.shuffle).lower()}')
            lines.append(f'allowed_hosts = {cfg.allowed_hosts!r}')
            lines.append(f'max_requests_per_user = {cfg.max_requests_per_user}')
            lines.append(f'max_queue = {cfg.max_queue}')
            lines.append(f'max_duration = {cfg.max_duration}')
            lines.append(f'voteskip_threshold = {cfg.voteskip_threshold}')
            lines.append(f'cooldown = {cfg.cooldown}')
            lines.append(f'send_interval = {cfg.send_interval}')
            lines.append(f'max_msg_len = {cfg.max_msg_len}')
            lines.append(f'announce_next = {str(cfg.announce_next).lower()}')
            lines.append("")
            lines.append(f'tts_voice = "{cfg.tts_voice}"')
            lines.append(f'tts_rate = {cfg.tts_rate}')
            lines.append(f'tts_duck = {cfg.tts_duck}')
            lines.append("")
            lines.append(f'auto_launch = {str(cfg.auto_launch).lower()}')
            lines.append(f'camfrog_exe = "{cfg.camfrog_exe}"')
            lines.append(f'client_title_re = "{cfg.client_title_re}"')
            lines.append(f'room = "{cfg.room}"')
            lines.append(f'join_uri_template = "{cfg.join_uri_template}"')
            lines.append(f'launch_timeout = {cfg.launch_timeout}')
            lines.append("")
            lines.append(f'blocked_users = {cfg.blocked_users!r}')
            lines.append(f'poll_interval = {cfg.poll_interval}')
            lines.append(f'log_file = "{cfg.log_file}"')
            lines.append(f'playlist_file = "{cfg.playlist_file}"')
            lines.append(f'search_limit = {cfg.search_limit}')
            lines.append(f'mpv_timeout = {cfg.mpv_timeout}')

            new_text = "\n".join(lines) + "\n"

            # Validate by parsing back
            tomllib.loads(new_text)

            p.write_text(new_text, "utf-8")

            # Re-read config to apply
            from .config import Config
            new_cfg = Config.load(str(p))
            self.e.cfg = new_cfg
            self.e.lang = new_cfg.lang
            self.e.volume = new_cfg.volume
            self.e.queue.shuffle = new_cfg.shuffle

            # Show save confirmation via say
            self.e.say(self.e.t("g_settings_saved"))

        except Exception as ex:
            log.exception("save settings failed")
            self.e.say(self.e.t("g_settings_save_failed", err=str(ex)))

    def close(self):
        self._closing = True
        self.e.shutdown()
        self.destroy()

    # ---- polling -------------------------------------------------------------
    def refresh(self):
        try:
            self._refresh()
        except (
            Exception
        ):  # one bad frame must not freeze the window: log it and keep polling
            log.exception("GUI refresh failed")
        finally:
            if not self._closing:
                self._ref = self.after(500, self.refresh)

    def _refresh(self):
        s = self.e.snapshot()
        t = s["current"]
        if t is not None and id(t) != self._last_track_id:
            self._last_track_id = id(t)
            self._launch_confetti()
        self._cur_dur = (t.duration or 0) if t else 0
        self._state = "idle" if not t else ("paused" if s["paused"] else "playing")
        if t:
            self.v_title.configure(text=t.title)
            self.v_sub.configure(text=f"{t.requester}  ·  {t.dur}")
            self.bar.set(s["position"] / t.duration if t.duration else 0)
            self.v_time.configure(text=f"{mmss(s['position'])} / {t.dur}")
        else:
            self.v_title.configure(text=self.e.t("g_nothing"))
            self.v_sub.configure(text="")
            self.bar.set(0)
            self.v_time.configure(text="")
        self._sync_pause()
        n = s["next"]
        self.v_next.configure(
            text=f"{self.e.t('g_up_next')}: {n.title} [{n.dur}] ({n.requester})"
            if n
            else ""
        )
        if not self.vol.dragging:
            self.vol.set(s["volume"])
            self.v_volpct.configure(text=f"{int(s['volume'])}%")
        self.c_shuffle.set_active(s["shuffle"])
        self.c_repeat.set_active(s["repeat"] == "one")
        items = [
            f"{i}. {q.title}  [{q.dur}]  ({q.requester})"
            for i, q in enumerate(s["queue"], 1)
        ]
        self._q_tracks = list(s["queue"])
        if items != self._q_cache:
            self._q_cache = items
            self.lb.delete(0, "end")
            self.lb.insert("end", *items)
        hist = [
            f"{i}. {q.title}  [{q.dur}]  ({q.requester})"
            for i, q in enumerate(s.get("history", []), 1)
        ]
        if hist != self._h_cache:
            self._h_cache = hist
            self.hist.delete(0, "end")
            self.hist.insert("end", *hist)
        new = min(self.e.chat_seq - self._seen, len(self.e.chat_log))
        if new > 0:
            self.chat.configure(state="normal")
            for who, text in list(self.e.chat_log)[-new:]:
                bot = who == self.e.cfg.bot_nick
                self.chat.insert("end", who + ": ", ("who", "bot") if bot else ("who",))
                self.chat.insert("end", text + "\n")
            extra = (
                int(self.chat.index("end-1c").split(".")[0]) - 1000
            )  # keep the log box bounded
            if extra > 0:
                self.chat.delete("1.0", f"{extra + 1}.0")
            self.chat.see("end")
            self.chat.configure(state="disabled")
        self._seen = self.e.chat_seq
