import sys
import time
import tkinter as tk

from camfrog_autodj.gui import App
from camfrog_autodj.models import Track
from test_core import make


def main() -> int:
    try:
        e = make()
        app = App(e)
    except tk.TclError as exc:
        print(f"TK_UNAVAILABLE: {exc}", file=sys.stderr)
        return 3

    try:
        e.current = Track("s", "Midnight City", 243, "bob")
        e.started_at = time.monotonic() - 60
        e.queue.add_request(Track("q", "Queued song", 100, "amy"))
        e.say("hello")
        app.update()
        assert app.v_title.cget("text") == "Midnight City"
        assert "Queued song" in app.lb.get(0)
        assert "hello" in app.chat.get("1.0", "end")
        app.set_lang("th")
        app.update()
        assert app.b_pause.cget("text") == "หยุดชั่วคราว"
        return 0
    finally:
        try:
            app.close()
        finally:
            e.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
