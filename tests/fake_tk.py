"""A strict stand-in for tkinter, so the GUI's logic can be exercised on machines without a display.
It rejects options that real Tk widgets / canvas items do not accept (the usual way a hand-written GUI breaks at
start-up) and records what was drawn. It does NOT render anything: the real-Tk smoke test covers that."""
import itertools
import types


class TclError(Exception):
    pass


def _s(*names):
    return set(names)


COMMON = _s("bg", "background", "bd", "borderwidth", "relief", "cursor", "highlightthickness",
            "highlightbackground", "highlightcolor", "takefocus", "width", "height")
OPTS = {
    "Tk": _s("bg", "background", "cursor", "menu"),
    "Frame": COMMON | _s("padx", "pady"),
    "Label": COMMON | _s("text", "font", "fg", "foreground", "anchor", "justify", "wraplength", "padx", "pady",
                         "textvariable", "image"),
    "Canvas": COMMON | _s("scrollregion", "insertbackground", "yscrollcommand", "xscrollcommand"),
    "Entry": COMMON | _s("fg", "foreground", "insertbackground", "font", "selectbackground", "selectforeground",
                         "show", "textvariable", "state", "justify", "exportselection"),
    "Listbox": COMMON | _s("fg", "foreground", "selectbackground", "selectforeground", "activestyle", "selectmode",
                           "font", "exportselection", "yscrollcommand", "xscrollcommand"),
    "Text": COMMON | _s("fg", "foreground", "wrap", "state", "padx", "pady", "font", "insertbackground",
                        "selectbackground", "selectforeground", "yscrollcommand", "xscrollcommand"),
    "Scrollbar": _s("orient", "command", "style", "takefocus", "cursor"),
    "Menu": _s("tearoff"),
}
ITEM_OPTS = {
    "polygon": _s("smooth", "fill", "outline", "width", "tags", "stipple", "dash"),
    "text": _s("text", "font", "fill", "anchor", "width", "tags", "justify"),
    "rectangle": _s("fill", "outline", "width", "tags", "stipple", "dash"),
    "oval": _s("fill", "outline", "width", "tags", "stipple", "dash"),
    "arc": _s("start", "extent", "style", "outline", "width", "fill", "tags", "dash"),
    "line": _s("fill", "width", "tags", "dash", "capstyle"),
}
PACK = _s("side", "fill", "expand", "padx", "pady", "ipadx", "ipady", "anchor", "before", "after", "in_")
GRID = _s("row", "column", "sticky", "padx", "pady", "columnspan", "rowspan", "ipadx", "ipady")


def _check(kind, opts, allowed):
    bad = set(opts) - allowed
    if bad:
        raise TclError(f"unknown option(s) {sorted(bad)} for {kind}")


class Misc:
    _kind = "Frame"
    _ids = itertools.count(1)

    def __init__(self, master=None, cnf=None, **kw):
        kw = {**(cnf or {}), **kw}
        _check(self._kind, kw, OPTS[self._kind])
        self.master, self._opts, self._after, self.binds = master, dict(kw), [], []
        self.destroyed = False

    # options
    def configure(self, cnf=None, **kw):
        kw = {**(cnf if isinstance(cnf, dict) else {}), **kw}
        _check(self._kind, kw, OPTS[self._kind])
        self._opts.update(kw)

    config = configure

    def cget(self, key):
        _check(self._kind, {key: 1}, OPTS[self._kind])
        return self._opts.get(key, "")

    __getitem__ = cget

    def __setitem__(self, k, v):
        self.configure({k: v})

    # geometry managers
    def pack(self, **kw):
        _check("pack", kw, PACK)
    pack_configure = pack

    def pack_forget(self):
        pass

    def grid(self, **kw):
        _check("grid", kw, GRID)

    def columnconfigure(self, *a, **k):
        pass
    rowconfigure = columnconfigure

    # misc window info
    def winfo_width(self):
        return 900

    def winfo_height(self):
        h = self._opts.get("height", 40)
        return int(h) if str(h).isdigit() else 40

    def winfo_fpixels(self, s):
        return 96.0

    def winfo_id(self):
        return 1

    def winfo_x(self):
        return 0
    winfo_y = winfo_x

    def focus_set(self):
        pass

    def focus_get(self):
        return None

    def bind(self, seq, fn=None, add=None):
        self.binds.append((seq, fn))

    bind_all = bind

    def bind_class(self, cls, seq=None, fn=None, add=None):
        self.binds.append((cls, seq, fn))

    def event_generate(self, *a, **k):
        pass

    def after(self, ms, fn=None, *a):
        self._after.append((ms, fn))
        return f"after#{len(self._after)}"

    def after_cancel(self, i):
        pass

    def update(self):
        pass
    update_idletasks = update

    def destroy(self):
        self.destroyed = True


class Tk(Misc):
    _kind = "Tk"

    def __init__(self, *a, **k):
        super().__init__(None)
        self._state = "normal"

    def title(self, t):
        self._title = t

    def geometry(self, g):
        self._geom = g

    minsize = maxsize = protocol = iconbitmap = lambda self, *a, **k: None

    def state(self, s=None):
        return self._state

    def mainloop(self):
        pass


class Frame(Misc):
    _kind = "Frame"


class Label(Misc):
    _kind = "Label"


class Menu(Misc):
    _kind = "Menu"

    def add_command(self, **k):
        pass


class Entry(Misc):
    _kind = "Entry"

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._text = ""

    def get(self):
        return self._text

    def delete(self, a, b=None):
        self._text = ""

    def insert(self, i, s):
        self._text += s

    def select_range(self, *a):
        pass

    def icursor(self, *a):
        pass


class Listbox(Misc):
    _kind = "Listbox"

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.items, self.selected = [], ()

    def delete(self, a, b=None):
        self.items = []

    def insert(self, where, *items):
        self.items.extend(items)

    def get(self, i, j=None):
        return self.items[i] if j is None else self.items[i:]

    def curselection(self):
        return self.selected

    def yview(self, *a):
        pass


class Text(Misc):
    _kind = "Text"

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.buf, self.tags = "", {}

    def insert(self, where, s, tags=()):
        if self._opts.get("state") == "disabled":
            raise TclError("text widget is disabled: insert ignored by real Tk, a bug in the caller")
        self.buf += s

    def delete(self, a, b=None):
        self.buf = ""

    def get(self, a, b=None):
        return self.buf

    def index(self, i):
        return f"{self.buf.count(chr(10)) + 1}.0"

    def see(self, i):
        pass

    def tag_configure(self, name, **kw):
        _check("tag", kw, _s("foreground", "font", "background", "underline"))
        self.tags[name] = kw

    def tag_add(self, *a):
        pass

    def yview(self, *a):
        pass


class Canvas(Misc):
    _kind = "Canvas"

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.items = {}

    def _new(self, kind, coords, kw):
        _check("canvas " + kind, kw, ITEM_OPTS[kind])
        i = next(self._ids)
        self.items[i] = (kind, list(coords), dict(kw))
        return i

    def create_polygon(self, *c, **k):
        return self._new("polygon", c[0] if len(c) == 1 else c, k)

    def create_text(self, *c, **k):
        return self._new("text", c, k)

    def create_rectangle(self, *c, **k):
        return self._new("rectangle", c, k)

    def create_oval(self, *c, **k):
        return self._new("oval", c, k)

    def create_arc(self, *c, **k):
        return self._new("arc", c, k)

    def create_line(self, *c, **k):
        return self._new("line", c, k)

    def coords(self, i, *c):
        self.items[i][1][:] = list(c[0]) if len(c) == 1 else list(c)

    def itemconfigure(self, i, **kw):
        _check("canvas " + self.items[i][0], kw, ITEM_OPTS[self.items[i][0]])
        self.items[i][2].update(kw)

    def delete(self, what):
        if what == "all":
            self.items = {}
        else:
            self.items.pop(what, None)


# ---- tkinter.font / ttk / filedialog -------------------------------------------------------
class Font:
    def __init__(self, root=None, family="x", size=10, weight="normal", **k):
        self.size = size

    def measure(self, text):
        return int(len(str(text)) * (self.size * 0.6) + 1)


font = types.SimpleNamespace(Font=Font, nametofont=lambda n: Font())


class Style:
    def __init__(self, *a):
        pass

    def theme_use(self, n):
        pass

    def configure(self, *a, **k):
        pass

    def map(self, *a, **k):
        pass


class _Scrollbar(Misc):
    _kind = "Scrollbar"

    def set(self, lo, hi):
        pass


class _TEntry(Entry):
    pass


ttk = types.SimpleNamespace(Style=Style, Scrollbar=_Scrollbar, Entry=_TEntry, Combobox=type("Combobox", (Entry,), {}),
                            Spinbox=type("Spinbox", (Entry,), {}))
filedialog = types.SimpleNamespace(askopenfilenames=lambda **k: (), askdirectory=lambda **k: "")
