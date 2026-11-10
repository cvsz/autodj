# Performance Report — CamfrogAutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`  
**Status:** Reviewed; no production-scale benchmark executed

## Observed measurements

- Test suite: 336 tests in ~15.6 s (pytest, Linux, Python 3.14.4).
- Library scan: `scan_folder` is bounded by `limit` (tracks) and `max_dirs` (sub-directories); skips symlinks and unreadable dirs per-entry; returns `[]` for missing roots. Large directories cannot scan forever.
- Playlist load: single read + JSON parse at startup; guarded by lock; corrupt file = `[]`.
- Chat poll interval: configurable `poll_interval` (default 0.5 s); "raise it if AutoDJ uses too much CPU" (README).
- Failure backoff: `min(30, 2^(n-1))` s; room announcements stop after 3 consecutive failures — prevents chat flood on a broken setup.

## Not measured (no realistic workload / host)

- Library scan time on a large local library (thousands of files).
- Memory usage over a long session.
- File-descriptor / process-leak measurement (mpv one-per-track, terminated after play).
- GUI frame time on a real display.
- MPV startup latency.

These require a Windows host with mpv, a media library, and a display. Marked BLOCKED, not estimated.
