# Playback Engine Review — CamfrogAutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`  
**Status:** Reviewed; real mpv playback not executable on this host

## MPV integration (`player.py:MpvPlayer`)

- One mpv process per track (`subprocess.Popen` argument list, `shell=False`).
- Flags: `--no-video --force-window=no --no-terminal --really-quiet --ytdl-format=bestaudio/best --input-ipc-server --log-file --volume`.
- `--script-opts=ytdl_hook-ytdl_path=<resolved yt-dlp>` so mpv's youtube hook uses the same yt-dlp as title lookups (`find_ytdlp`).
- `CREATE_NO_WINDOW` on Windows (no console flash).
- IPC: named pipe (Windows) / UNIX socket (Linux) for `get_time_pos`, `seek`, `set_pause`, `set_volume`.
- `play_file` (TTS) uses `subprocess.run` with a 30 s timeout.
- Termination: `stop()` sets `skipped=True` and `terminate()`; `play()` on hang terminates then kills after 5 s.
- Log cleanup: mpv log file removed after reporting (`_report`).

## Playback lifecycle (`engine.py:_player_loop` / `_play_one_track`)

- Pops from `PlayQueue` (requests first, then looping autoplay pool).
- `mpv_timeout` is a grace period over known duration, not a hard cap (longer songs not cut).
- Failure backoff: `fail_delay(n) = min(30, 2^(n-1))`; after 3 consecutive failures, room announcements stop (only log) to prevent flood.
- `repeat == "one"` loops the same track; `skipped` breaks the loop.
- `position()`: mpv IPC `time-pos`, fallback to wall-clock excluding pauses.

## Findings

- F-002 (IPC read block) and F-003 (live stream blocks loop) documented above.
- No orphaned-process claim: `stop()`/`play()` terminate and kill mpv; `shutdown()` calls `player.stop()`.

## Verdict

Playback design is sound for the local-file and YouTube (via yt-dlp) paths it supports. Real mpv process startup, IPC, device disconnection, and crash behavior **cannot be executed on this Linux host** (no mpv, no audio device, no Windows). Marked BLOCKED for runtime validation; not claimed as passing.
