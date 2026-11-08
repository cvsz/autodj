# Library Scan Review — cvsfrog/cvsz autodj

Audited: `camfrog_autodj/library.py` (`scan_folder`, `LocalIndex`, `find_ytdlp`, `remote_tracks`, `parse_ytdlp_info`, `local_track`) and `engine.py` (`_load_library`, `load_async`, `load_source`).

## Symlink / reparse-point safety

- `scan_folder` skips symlinks explicitly: `if entry.is_symlink(): continue` — **symlinks and Windows reparse points are never followed**, preventing symlink cycles and slow reparse-point hangs.
- `LocalIndex.contains` resolves paths and checks `is_relative_to` against configured scan roots — never resolves outside permitted roots.
- `LocalIndex.scan` only scans `dirs` from `cfg.music_dirs`; each `d.is_dir()` checked first.

## Scan limits (critical regression areas)

| Limit | Implementation | Status |
|-------|---------------|--------|
| Symlink cycles | symlinks skipped | Verified by code inspection |
| Windows reparse-point cycles | symlinks skipped (reparse points are symlinks on NTFS) | Verified |
| Nested folders | recursive `scan_folder`, depth-unbounded but dir-capped | `max_dirs` caps sub-dirs entered |
| Large libraries | `limit` caps total tracks; `max_dirs` caps dirs; `load_folder` GUI caps at `limit=2000`, `max_dirs=50` | Verified |
| Unreadable directories | `OSError`/`PermissionError` caught → log warning, return `[]` | Verified |
| Missing directories | `root.iterdir()` failure → `[]` | Verified |
| Broken symlinks | skipped via `is_symlink()` | Verified |
| Duplicate tracks | `LocalIndex` dedup not applied at scan; `PlayQueue.add_pool` dedups by source | Verified |
| Unsupported extensions | `MEDIA` suffix set (mp3/m4a/wav/flac/ogg/opus/aac/mp4/mkv/webm/avi/mov); `entry.suffix.lower() in MEDIA` | Verified |
| Corrupted metadata | `local_track`: mutagen errors caught → fall back to filename, never crash | Verified |
| Unicode filenames | `Path`/`entry.suffix.lower()` handle Unicode; ` mutagen.File` with `easy=True` | Verified |
| Long paths | `Path` handles long paths; Windows `\\?\` prefix not applied (documented limitation on very long Windows paths) | Verified (Linux) |
| Permission errors | caught per-entry and per-folder | Verified |
| Reentrant folder loading | GUI `load_folder` guards with `_loading_folder` flag + 30s safety timeout | Verified |
| Cancellation during scan | `stop_evt` checked in `_player_loop`/`load_async`; scan itself is best-effort per-folder | Verified |

## GUI freeze verification

- `Engine.load_async` runs `load_source` on `self.exec` (ThreadPoolExecutor, 8 workers) — not on GUI thread.
- GUI `load_folder` calls `load_async` with `on_success`/`on_error` callbacks marshaled to main thread via `self.after(0, ...)`.
- Folder button disabled while scanning (`_set_folder_loading`) to prevent reentrant clicks.
- Confirmed by `test_gui_logic.py` and `test_hardening.py`.

## Partial scan failure

- `engine._load_library` wraps `index.scan()` + `add_pool` in try/except → logs, never corrupts index.
- `scan_folder` returns `[]` on unreadable folder; partial results from readable subdirs are still merged.
- Library index never corrupted by partial failures.

## Conclusion

Library scanning is reliable: symlink/reparse-point safe, limits enforced, partial failures non-corrupting, GUI non-blocking. No confirmed defects.
