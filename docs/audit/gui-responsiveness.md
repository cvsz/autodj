# GUI Responsiveness — CamfrogAutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`  
**Status:** Reviewed (Tk GUI); real-Tk smoke test not executable headless on this host

## Threading model

- `Engine` runs daemon threads: `_sender`, `_player_loop`, `_load_all`, `_chat_loop`, `_auto_reply_loop`, `_im_auto_reply_loop` (`engine.py:start()`).
- Tk GUI (`gui.py:App`) polls `Engine.snapshot()` every 500 ms (`refresh()`) and animates at ~30 fps (`_tick()`).
- All GUI updates from background callbacks are marshaled to the main thread via `tk.after(0, ...)` (`gui.py:_set_hint`, `add()`/`add_files()` on_success/on_error, folder-load callbacks).
- Blocking work (yt-dlp lookup, folder scan, playlist load) runs in `Engine.exec` (`ThreadPoolExecutor(8)`) or `load_async`, never on the GUI thread.
- Folder scan button disabled while scanning; 30 s safety timeout re-enables it (`gui.py:load_folder`).

## Busy/disabled state

- `PillButton.configure(state=...)` toggles enabled/disabled; folder button disabled during scan; add button disabled during resolution (`_set_adding_state`).
- Repeated folder clicks guarded by `self._loading_folder` flag.
- mpv-missing warning banner shown when `player.available()` is False.

## Shutdown

- `App.close()` cancels `after` timers, calls `Engine.shutdown()` (sets stop event, stops player, closes adapter, shuts down executor, joins threads with 5 s timeout), then destroys the window.

## Findings

- F-002: `position()` → mpv IPC `_cmd_get` can block on Windows if mpv is unresponsive (documented, BLOCKED from validation).
- Real-Tk rendering on screen not verified (no display/Camfrog on this host); `test_gui_smoke` is environment-dependent.

## Verdict

GUI design is thread-safe and non-blocking by construction. Windows display behavior and real Camfrog window interaction are BLOCKED (no Windows/display/Camfrog host).
