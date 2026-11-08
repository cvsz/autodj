# Performance Report — cvsz/autodj

**BLOCKED for real measurement.** No profiling run against real mpv / large library / real Camfrog in this environment. The following are design-level assessments from source inspection, not measurements.

## Design-level performance characteristics

| Area | Mechanism | Assessment |
|------|-----------|------------|
| Library scan | `scan_folder` with `limit`/`max_dirs` caps; symlinks skipped; executor offload | Capped; non-blocking GUI |
| GUI refresh | 500 ms poll of `snapshot()`; animations ~30 fps; per-frame exception isolation | Lightweight |
| Playback | one mpv process per track; IPC commands; temp log cleaned | No persistent per-track overhead |
| Queue ops | `RLock`-guarded lists; `peek`/`pop` O(1); dedup via set | Efficient |
| Chat read | `poll_interval` (default 0.5s) sleep between polls; 300-line tail | Configurable; bounded |
| TTS | single worker thread; 60s timeout per synthesis | Serialized, no overlap |
| Shutdown | `stop_evt` + 5s thread joins + player stop | Bounded |

## What would need measuring (BLOCKED)

- Library scan time on large libraries
- Memory usage / file-descriptor leaks
- MPV startup latency
- Playback command latency
- GUI responsiveness on large libraries
- Shutdown time

No memory leaks, FD leaks, deadlocks, or reentrant GUI handlers were found by inspection, but these require real measurement on Windows with mpv/Camfrog.

## Conclusion

No performance defects found by inspection. Performance claims are NOT VERIFIED (no measurements taken); real measurement is BLOCKED in this environment.
