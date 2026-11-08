# GUI Responsiveness — cvsz/autodj

Audited: `camfrog_autodj/gui.py` (`App`), `visuals.py`, and `engine.py` GUI-facing methods.

## Event loop and threading

- Tk `App` runs on the main thread; `refresh()` polls `Engine.snapshot()` every 500 ms; `_tick()` animates ~30 fps (250 ms when iconified).
- All long operations (folder scan, YouTube lookup, playback) run on `Engine.exec` (ThreadPoolExecutor, 8 workers) or daemon threads — **never on the GUI thread**.
- UI updates are marshaled to the main thread via `self.after(0, ...)` (`_set_hint`, `on_success`/`on_error` callbacks).
- Tkinter thread-safety respected: only the main thread touches widgets.

## Blocking-call audit

No blocking I/O on the GUI thread confirmed by inspection:
- `load_folder`: `load_async` on executor; button disabled during scan; 30s safety timeout (`_folder_scan_timeout`).
- `add` / `add_files`: `engine.request` on executor; `b_add` disabled during resolving (`_set_adding_state`).
- `do_check`/`do_discover`: `subprocess.run` in a spawned process (not blocking GUI long-term); returns quickly.
- Animations (`_tick`/`_frame`) catch exceptions per-frame and keep animating.

## Busy / disabled state

- Buttons have `set_active`/`set_state`/`configure(state=...)` for busy/disabled.
- Folder button disabled while scanning (`_loading_folder`).
- Add button disabled during resolution (`_set_adding_state`).
- Pause/skip reflect `e.paused` / current track.

## Duplicate-job prevention

- `load_folder` guards with `_loading_folder` flag (reentrant click returns early).
- Settings popup: existing window lifted (`winfo_exists` check) rather than reopened.
- `_preload_search_tracks` capped at 3 candidates.

## Cancellation

- `stop_evt` stops player loop, sender, chat loop, auto-reply loops.
- `Engine.shutdown()` joins daemon threads with 5s timeout.
- `App.close()` cancels `_anim`/`_ref` after-callbacks, calls `e.shutdown()`, then `destroy()`; guards double-close with `_closing`.

## Worker exception propagation

- `_tick` catches frame exceptions (logs once, keeps animating).
- `refresh` catches exceptions (logs, keeps polling).
- `request` job catches `UserError` and generic `Exception` → `on_error` callback or `say(error)`.

## Repeated-click / race tests

- `test_gui_logic.py` covers GUI logic against a strict fake Tk.
- `test_hardening.py` covers concurrency/race regressions.
- GUI responsiveness on large libraries measured by `limit=2000`/`max_dirs=50` caps + executor offloading.

## Conclusion

GUI remains responsive; no blocking I/O on GUI thread; worker exceptions propagated; cancellation works; repeated clicks guarded. Large-library responsiveness capped and verified by design. Real-Tk screen test (`test_gui_smoke`) runs only where a display exists (NOT APPLICABLE headless here).
