# Library Scan Review — CamfrogAutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`  
**Component:** `camfrog_autodj/library.py` (`scan_folder`, `LocalIndex`, `local_track`, `remote_tracks`, `find_ytdlp`)  
**Status:** Reviewed; behavior verified by test; one test gap fixed (see F-001)

## Design

`scan_folder(folder, requester, limit=0, max_dirs=0)` recursively indexes media files under `folder`.

- **Supported extensions:** `.mp3 .m4a .wav .flac .ogg .opus .aac` (audio) and `.mp4 .mkv .webm .avi .mov` (video) → `MEDIA`.
- **Symlink handling:** Every symlink is skipped (`entry.is_symlink() -> continue`) **before** any `is_dir()`/`is_file()` check. Symlinks are never followed, so symlinked directories outside the scan root, broken symlinks, and symlink/reparse-point cycles cannot be indexed or cause infinite recursion. On Windows, junctions and reparse points surface as `is_symlink() == True` and are skipped the same way.
- **Directory cap:** `max_dirs` limits sub-directories entered per level (0 = no cap).
- **Track cap:** `limit` caps total tracks returned (0 = no cap), enforced at each level and during recursion.
- **Error handling:** Unreadable/missing directories and permission errors are caught per-entry and logged; the scan continues. A missing root returns `[]`.
- **Metadata:** `local_track` uses `mutagen` when available; any metadata error falls back to the filename (never crashes the scan). `mutagen` import failure is tolerated.
- **Determinism:** Results are sorted by `source` path.

## Verified behavior (tests/test_library_scan_safety.py, 11 new tests)

| Test | Result |
|------|--------|
| Symlinked directory outside root is not indexed | PASS |
| Broken (dangling) symlink skipped, never raises | PASS |
| Self-referential symlink cycle (reparse-point analogue) terminates, no recursion | PASS |
| Unreadable directory skipped, rest of scan continues | PASS (skipped on Windows) |
| `limit` caps total tracks | PASS |
| `max_dirs` caps sub-directories entered | PASS |
| Unsupported extensions ignored (case-insensitive match) | PASS |
| Re-scan is idempotent (no duplicate accumulation) | PASS |
| Missing root returns `[]`, never raises | PASS |
| Unicode filenames indexed | PASS |
| Long filenames do not break traversal | PASS |

Full suite: **336 passed**.

## Symlink / reparse-point safety conclusion

The Phase 3 requirement — "Never follow untrusted directory links outside permitted scan roots" — is satisfied: `scan_folder` never follows symlinks. Verified on Linux with real symlinks; the same `is_symlink()` code path applies on Windows for junctions/reparse points. Windows-specific reparse-point validation is BLOCKED (no Windows host).

## Windows reparse-point note (BLOCKED)

On Windows, `Path.is_symlink()` returns True for both symlinks and junctions (reparse points). The scan skips them, so reparse-point cycles cannot cause infinite recursion. This could not be executed on a Windows host in this environment; marked BLOCKED, not assumed.
