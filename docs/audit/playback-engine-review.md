# Playback Engine Review — cvsz/autodj

Audited: `camfrog_autodj/player.py` (`MpvPlayer`) and `engine.py` (`_player_loop`, `_play_one_track`).

## MPV integration

- **Discovery:** `MpvPlayer.available()` → `resolve_executable(cfg.mpv_path)`.
- **Executable resolution:** `paths.resolve_executable` — explicit paths authoritative; relative-with-separator anchored to app dir; bare names via `shutil.which`; returns `""` (not a silently substituted binary) when missing.
- **Version compatibility:** `doctor._ytdlp_version` reports yt-dlp version; mpv version not parsed (mpv has no simple version flag used).
- **Process startup:** `subprocess.Popen(cmd, **kw)` with argument list (never shell); `CREATE_NO_WINDOW` on Windows.
- **Process termination:** `stop()` → `p.terminate()`; hang path → `terminate()` then `kill()` with 5s wait.
- **IPC:** named pipe (Windows) / unix socket (Linux) `--input-ipc-server`; `get_time_pos`, `seek`, `set_pause`, `set_volume` via IPC JSON commands.
- **Playback commands:** pause/resume, seek, volume, next/previous (via `skip`/`stop`).
- **Error handling:** `_report` reads mpv log for failure reasons; `_try_play` catches exceptions; `_track_failed` backoff.
- **Output device:** `--audio-device=` from `cfg.audio_device`.
- **Audio format:** `--ytdl-format=bestaudio/best`; `--no-video --force-window --no-terminal --really-quiet`.
- **Device disconnection / crashes:** handled by mpv exit code + log; failure announced max 3 times then backoff.
- **Shutdown cleanup:** `Engine.shutdown()` → `player.stop()`; temp mpv log removed in `_report` finally; `os.remove` best-effort.

## Hang detection (not a cap)

`mpv_timeout` is a **grace period on top of track length**, never a flat cap. Time spent paused excluded. Unknown duration (live) = no limit. This was a historical bug (flat cap cut long songs) — fixed and tested (`test_hardening.py` F2).

## Orphaned processes

No orphans: each track = one mpv process; `stop()` terminates; `kill()` fallback; temp log cleaned. `Engine.shutdown()` stops player.

## Tests

Covered by `test_play_flow.py`, `test_hardening.py` (F2 failure throttling/backoff), `test_executable_paths.py`.

## Gaps (environment-limited)

- Real mpv playback not exercised here (fake mpv in tests).
- `MpvPlayer._cmd_get` Windows named-pipe read has no read timeout; blocks until mpv responds or pipe closes. GUI calls `position()` on the GUI thread poll (500ms). Classified as a residual risk (Windows-only, cannot reproduce here).

## Conclusion

MPV lifecycle verified by design and tests; no orphaned processes; hang detection is a grace period not a cap; subprocess uses argument lists. Real-mpv runtime validation is BLOCKED (no mpv/Windows here).
