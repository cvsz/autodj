"""Settings -> Ads list: the ads-list.json editor window.

``AdsDraft`` holds the list being edited (no Tk, unit-tested); ``AdsEditor`` is the
window. Saving goes through :func:`autodj.ads_list.save` (atomic, ``.bak`` kept) and
the running ads loop reloads the file on its next slot.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from . import ads_list


def _one_line(text: str) -> str:
    """Room messages are one line: newlines and repeated spaces collapse to one space."""
    return " ".join(text.split())


class AdsDraft:
    """The ads being edited, with an unsaved-changes flag."""

    def __init__(self, items: list[str]):
        self.items = list(items)
        self.dirty = False

    def _check(self, text: str) -> str:
        s = _one_line(text)
        if not s:
            raise ValueError("empty")
        if len(s) > ads_list.MAX_AD_CHARS:
            raise ValueError(f"{len(s)} > {ads_list.MAX_AD_CHARS}")
        return s

    def add(self, text: str) -> int:
        self.items.append(self._check(text))
        self.dirty = True
        return len(self.items) - 1

    def update(self, index: int, text: str) -> int:
        self.items[index] = self._check(text)
        self.dirty = True
        return index

    def delete(self, index: int) -> int | None:
        del self.items[index]
        self.dirty = True
        return min(index, len(self.items) - 1) if self.items else None

    def move(self, index: int, step: int) -> int:
        j = index + step
        if not 0 <= j < len(self.items):
            return index
        self.items[index], self.items[j] = self.items[j], self.items[index]
        self.dirty = True
        return j

    def save(self, path: str) -> None:
        self.items = ads_list.save(path, self.items)
        self.dirty = False


class AdsEditor:
    """The editor window. *app* is the AutoDJ GUI (fonts, px(), engine, palette)."""

    def __init__(self, app: Any):
        from . import gui as g  # the live palette (it changes with the theme)

        self.app, self.g, self.t = app, g, app.e.t
        self.path = ads_list.resolve_path(app.e.cfg.auto_reply_file, app.e.cfg_path)
        self.draft = AdsDraft(ads_list.load(self.path))
        self.win = tk.Toplevel(app, bg=g.SURFACE)
        self.win.title(self.t("g_ads_editor_title"))
        self.win.transient(app)
        self.win.geometry(f"{app.px(720)}x{app.px(520)}")
        self.win.minsize(app.px(480), app.px(360))
        self._build()
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self._refresh(0 if self.draft.items else None)
        self._on_select()

    # ---- layout -----------------------------------------------------------
    def _build(self) -> None:
        g, app, pad = self.g, self.app, self.app.px(10)
        self.info = tk.Label(
            self.win, bg=g.SURFACE, fg=g.MUTED, font=app.f_small, anchor="w", justify="left"
        )
        self.info.pack(fill="x", padx=pad, pady=(pad, 0))
        if not app.e.cfg.auto_reply_enabled:
            tk.Label(
                self.win,
                bg=g.SURFACE,
                fg=g.PINK,
                font=app.f_small,
                anchor="w",
                text=self.t("g_ads_disabled_note"),
            ).pack(fill="x", padx=pad)
        mid = tk.Frame(self.win, bg=g.SURFACE)
        mid.pack(fill="both", expand=True, padx=pad, pady=pad)
        self.lb = app._listbox(mid)
        self.lb.configure(selectmode="browse")
        sb = ttk.Scrollbar(mid, orient="vertical", command=self.lb.yview)
        self.lb.configure(yscrollcommand=sb.set)
        self.lb.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.lb.bind("<<ListboxSelect>>", self._on_select)
        self.editor = tk.Text(
            self.win,
            height=3,
            wrap="word",
            bg=g.SURFACE2,
            fg=g.TEXT,
            insertbackground=g.CYAN,
            relief="flat",
            font=app.f_list,
            highlightthickness=1,
            highlightbackground=g.BORDER,
            highlightcolor=g.VIOLET,
            bd=0,
            undo=True,
        )
        self.editor.pack(fill="x", padx=pad)
        self._buttons(pad)

    def _buttons(self, pad: int) -> None:
        g, app = self.g, self.app
        bar = tk.Frame(self.win, bg=g.SURFACE)
        bar.pack(fill="x", padx=pad, pady=pad)
        spec = (
            ("g_ads_add", self.add, "ghost", "left"),
            ("g_ads_update", self.update, "ghost", "left"),
            ("g_ads_delete", self.delete, "danger", "left"),
            ("g_ads_up", lambda: self.move(-1), "ghost", "left"),
            ("g_ads_down", lambda: self.move(1), "ghost", "left"),
            ("g_ads_close", self.close, "ghost", "right"),
            ("g_ads_save", self.save, "primary", "right"),
        )
        gap = app.px(6)
        for key, cmd, kind, side in spec:
            b = g.PillButton(
                bar,
                command=cmd,
                kind=kind,
                font=app.f_bold,
                icon_font=app.f_icon,
                bg=g.SURFACE,
                height=app.px(34),
                minw=app.px(70),
            )
            b.configure(text=self.t(key))
            b.pack(side=side, padx=(0, gap) if side == "left" else (gap, 0))

    # ---- state ------------------------------------------------------------
    def _refresh(self, select: int | None = None) -> None:
        self.lb.delete(0, "end")
        for i, m in enumerate(self.draft.items, 1):
            self.lb.insert("end", f"{i}. {m}")
        if select is not None and 0 <= select < len(self.draft.items):
            self.lb.selection_set(select)
            self.lb.see(select)
        mark = " *" if self.draft.dirty else ""
        count = self.t("g_ads_count").format(n=len(self.draft.items))
        self.info.configure(text=f"{self.path}\n{count}{mark}")

    def _selected(self) -> int | None:
        sel = self.lb.curselection()
        return int(sel[0]) if sel else None

    def _text(self) -> str:
        return self.editor.get("1.0", "end")

    def _set_text(self, text: str) -> None:
        self.editor.delete("1.0", "end")
        if text:
            self.editor.insert("1.0", text)

    def _on_select(self, _event: object = None) -> None:
        i = self._selected()
        if i is not None:
            self._set_text(self.draft.items[i])

    def _error(self, key: str, **kw: object) -> None:
        messagebox.showerror(
            self.t("g_ads_editor_title"), self.t(key).format(**kw), parent=self.win
        )

    def _edit(self, action) -> None:
        """Run *action* (returns the row to select); too long -> error, empty -> ignored."""
        if len(_one_line(self._text())) > ads_list.MAX_AD_CHARS:
            n = len(_one_line(self._text()))
            self._error("g_ads_too_long", n=n, max=ads_list.MAX_AD_CHARS)
            return
        try:
            row = action()
        except ValueError:  # empty text
            return
        self._refresh(row)

    # ---- actions ----------------------------------------------------------
    def add(self) -> None:
        def run() -> int:
            row = self.draft.add(self._text())
            self._set_text("")
            return row

        self._edit(run)

    def update(self) -> None:
        i = self._selected()
        if i is not None:
            self._edit(lambda: self.draft.update(i, self._text()))

    def delete(self) -> None:
        i = self._selected()
        if i is not None:
            self._set_text("")
            self._refresh(self.draft.delete(i))

    def move(self, step: int) -> None:
        i = self._selected()
        if i is not None:
            self._refresh(self.draft.move(i, step))

    def save(self) -> bool:
        try:
            self.draft.save(self.path)
        except (ValueError, OSError) as ex:
            self._error("g_ads_save_failed", err=ex)
            return False
        self._refresh(self._selected())
        return True

    def close(self) -> None:
        if self.draft.dirty:
            answer = messagebox.askyesnocancel(
                self.t("g_ads_editor_title"), self.t("g_ads_unsaved"), parent=self.win
            )
            if answer is None or (answer and not self.save()):
                return
        self.app._ads_editor = None
        self.win.destroy()

    def show(self) -> None:
        self.win.deiconify()
        self.win.lift()
        self.win.focus_set()
