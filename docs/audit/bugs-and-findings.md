# Bugs and Findings — CamfrogAutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`  
**Method:** Full source review of `camfrog_autodj/` (all modules), `tests/`, `tools/`, build scripts, and installer scripts. No destructive commands run. User artifacts preserved.

## Findings summary

No Critical or High severity defects were found in the application code. The codebase has already undergone extensive remediation (135 merged PRs). The findings below are the issues identified in this audit, with their classification, exact location, and disposition.

## F-001: Library scan symlink/reparse-point safety — previously untested (FIXED)

- **Severity:** Medium (defense-in-depth)
- **Location:** `camfrog_autodj/library.py:52-90` (`scan_folder`)
- **Description:** `scan_folder` skips all symlinks (`entry.is_symlink() -> continue`), so symlinked directories outside scan roots, broken symlinks, and symlink/reparse-point cycles are never followed. This satisfies the Phase 3 safety requirement ("Never follow untrusted directory links outside permitted scan roots"), but there were **no regression tests** covering symlink cycles, Windows reparse points, broken symlinks, or unreadable directories.
- **Root cause:** Test gap, not a code defect.
- **Fix:** Added `tests/test_library_scan_safety.py` with 11 regression tests covering symlinked outside directories, broken symlinks, self-referential symlink cycles (reparse-point analogue), unreadable directories, track/dir limits, unsupported extensions, idempotent re-scan, missing roots, and Unicode/long filenames.
- **Status:** FIXED. Verified by `python3 -m pytest tests/test_library_scan_safety.py` (11 pass) and full suite (336 pass).

## F-002: GUI `position()` → mpv IPC read can block (Windows only)

- **Severity:** Low
- **Location:** `camfrog_autodj/player.py:247-287` (`_cmd_get`), called from `engine.py:377` (`position()`)
- **Description:** On Windows, `get_time_pos()` opens the mpv named pipe `r+b` and reads until a newline with no read timeout. If mpv stops responding while the pipe remains open, the read blocks. `position()` is called from the GUI poll loop every 500 ms (`gui.py:2240`), so a prolonged block would freeze the GUI.
- **Current behavior:** `open(ipc, "r+b")` raises `OSError` when the pipe is gone (caught → `None`), so a dead mpv does not block. Only a live-but-unresponsive mpv is a risk.
- **Disposition:** Documented as a residual risk. Not changed because the fix (non-blocking pipe or read timeout) is Windows-only and cannot be validated on this Linux host. Marked BLOCKED for Windows validation.

## F-003: MPV "live/unknown duration" player loop can block indefinitely

- **Severity:** Low
- **Location:** `camfrog_autodj/player.py:89-101` (`_wait_for_mpv_end`)
- **Description:** When track duration is unknown (live streams), `limit = None` and `p.wait(timeout=None)` blocks until mpv exits. A never-ending live stream stalls the player loop. Documented in `player.py` docstring ("Unknown duration (live) = no limit") as intentional.
- **Disposition:** Intentional design; documented, not a bug.

## F-004: Settings dialog manually re-serializes config.toml

- **Severity:** Low
- **Location:** `camfrog_autodj/gui.py:1985-2191` (`save_settings`)
- **Description:** The settings dialog builds `config.toml` text by hand rather than round-tripping through `Config.load`/`tomllib` dump. It re-validates via `_validate`, so invalid values are rejected before write, but any config key added to `Config` and not added to the manual serialization would be silently dropped on save.
- **Disposition:** Documented. The dialog re-reads and re-applies config after save, mitigating drift. No code change (avoid widening scope).

## F-005: GPG signing unavailable in this environment (BLOCKER)

- **Severity:** High (process, not code)
- **Location:** `.gitconfig` (`commit.gpgsign = true`, `gpg.proom = gpg-loopback.sh`)
- **Description:** GPG signing requires `GPG_PASSPHRASE` (not set) and a TTY for pinentry (none available). Signed commits as `cvsz` cannot be produced here.
- **Disposition:** Reported as a blocker; not faked. See docs/audit/gpg-review-merge-evidence.md.

## F-006: Windows build/installer not executable on this host (BLOCKED)

- **Severity:** High (process, not code)
- **Location:** `build.ps1`, `installer.nsi`, `scripts/build_installer.ps1`, PyInstaller spec
- **Description:** No Windows host, `makensis`, or Wine NSIS available. PyInstaller `.exe`, NSIS installer, and Authenticode signing cannot be built or verified.
- **Disposition:** Marked BLOCKED, not claimed as passing.

## Resolved / previously fixed (regression-tested)

The following historical defects are resolved and covered by tests in `tests/test_hardening.py`, `tests/test_play_flow.py`, `tests/test_production_remediation.py`:
- Bot acting on its own echo lines (F1)
- Queue flood / broken-track announcement flood (`MAX_FAIL_ANNOUNCE`, backoff)
- Config TOML syntax errors with `^` marker (`config.py:_syntax_message`)
- Playlist corrupt/missing file = empty, never fatal (`playlist.py`)
- Load-folder crash on permission-denied directories (`gui.py:load_folder`, `library.py:scan_folder`)
- Log file PermissionError on Program Files install (`__main__.py:_setup_log_file`, `doctor.py`)
- Auto-launch NameError / GUI crash (`launcher.py`, `__main__.py:_auto_launch`)
- NSIS installer warnings / `MUI_ABORTWARNING` / `VI_*` defines (`installer.nsi`)
- MPV timeout/hung-process termination (`player.py:_wait_for_mpv_end`)
- yt-dlp TLS/CA-bundle fallback (`library.py:_extract_exe`/`_extract_module`)
