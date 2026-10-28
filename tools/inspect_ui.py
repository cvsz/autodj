"""List Camfrog windows, or dump one window's control tree for view_/input_ settings.
  python tools/inspect_ui.py --list                 show every visible window matching the pattern
  python tools/inspect_ui.py ".*Camfrog.*" [N]      dump the Nth match (default 0)
Open a room window first. Use a tighter pattern (e.g. the room name) if several match."""
import sys
from pywinauto import Desktop
from camfrog_autodj.windows import candidates

args = [a for a in sys.argv[1:] if a != "--list"]
pat = args[0] if args else ".*Camfrog.*"
cs = candidates(pat, visible_only=False)
for i, c in enumerate(cs):
    print(f"[{i}] exe={c.exe!r} pid={c.pid} class={c.cls!r} title={c.title!r}")
if "--list" not in sys.argv:
    n = int(args[1]) if len(args) > 1 else 0
    Desktop(backend="uia").window(handle=cs[n].handle).print_control_identifiers()
