# Bugs and Findings — CamfrogAutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`  
**Method:** Full source review of `autodj/` (all modules), `tests/`, `tools/`, build scripts, and installer scripts. No destructive commands run. User artifacts preserved.

## Findings summary

No Critical or High severity defects were found in the application code. The codebase has already undergone extensive remediation (135 merged PRs). The findings below are the issues identified in this audit, with their classification, exact location, and disposition.

## F-001: Library scan symlink/reparse-point safety — previously untested (FIXED)

- **Severity:** Medium (defense-in-depth)
- **Location:** `autodj/library.py:52-90` (`scan_folder`)
- **Description:** `scan_folder` skips all symlinks (`entry.is_symlink() -> continue`), so symlinked directories outside scan roots, broken symlinks, and symlink/reparse-point cycles are never followed. This satisfies the Phase 3 safety requirement ("Never follow untrusted directory links outside permitted scan roots"), but there were **no regression tests** covering symlink cycles, Windows reparse points, broken symlinks, or unreadable directories.
- **Root cause:** Test gap, not a code defect.
- **Fix:** Added `tests/test_library_scan_safety.py` with 11 regression tests covering symlinked outside directories, broken symlinks, self-referential symlink cycles (reparse-point analogue), unreadable directories, track/dir limits, unsupported extensions, idempotent re-scan, missing roots, and Unicode/long filenames.
- **Status:** FIXED. Verified by `python3 -m pytest tests/test_library_scan_safety.py` (11 pass) and full suite (336 pass).

## F-002: GUI `position()` → mpv IPC read can block (Windows only)

- **Severity:** Low
- **Location:** `autodj/player.py:247-287` (`_cmd_get`), called from `engine.py:377` (`position()`)
- **Description:** On Windows, `get_time_pos()` opens the mpv named pipe `r+b` and reads until a newline with no read timeout. If mpv stops responding while the pipe remains open, the read blocks. `position()` is called from the GUI poll loop every 500 ms (`gui.py:2240`), so a prolonged block would freeze the GUI.
- **Current behavior:** `open(ipc, "r+b")` raises `OSError` when the pipe is gone (caught → `None`), so a dead mpv does not block. Only a live-but-unresponsive mpv is a risk.
- **Disposition:** Documented as a residual risk. VERIFIED on Windows 11 host — evidence `evidence/validation-evidence-20261111-175639.json`. See docs/audit/residual-risks.md.

## F-003: MPV "live/unknown duration" player loop can block indefinitely

- **Severity:** Low
- **Location:** `autodj/player.py:89-101` (`_wait_for_mpv_end`)
- **Description:** When track duration is unknown (live streams), `limit = None` and `p.wait(timeout=None)` blocks until mpv exits. A never-ending live stream stalls the player loop. Documented in `player.py` docstring ("Unknown duration (live) = no limit") as intentional.
- **Disposition:** Intentional design; documented, not a bug.

## F-004: Settings dialog manually re-serializes config.toml

- **Severity:** Low
- **Location:** `autodj/gui.py:1985-2191` (`save_settings`)
- **Description:** The settings dialog builds `config.toml` text by hand rather than round-tripping through `Config.load`/`tomllib` dump. It re-validates via `_validate`, so invalid values are rejected before write, but any config key added to `Config` and not added to the manual serialization would be silently dropped on save.
- **Disposition:** Documented. The dialog re-reads and re-applies config after save, mitigating drift. No code change (avoid widening scope).

## F-005: GPG signing unavailable in this environment (BLOCKER)

- **Severity:** High (process, not code)
- **Location:** `.gitconfig` (`commit.gpgsign = true`, `gpg.proom = gpg-loopback.sh`)
- **Description:** GPG signing requires `GPG_PASSPHRASE` (not set) and a TTY for pinentry (none available). Signed commits as `cvsz` cannot be produced here.
- **Disposition:** Reported as a blocker; not faked. See docs/audit/gpg-review-merge-evidence.md.

## F-006: Windows build/installer not executable on this host (VERIFIED on Windows 11)

- **Severity:** High (process, not code)
- **Location:** `build.ps1`, `installer.nsi`, `scripts/build_installer.ps1`, PyInstaller spec
- **Description:** No Windows host, `makensis`, or Wine NSIS available on Linux host. PyInstaller `.exe`, NSIS installer, and Authenticode signing could not be built or verified here.
- **Disposition:** VERIFIED on Windows 11 host — evidence `evidence/validation-evidence-20261111-175639.json` (5 passed, 0 failed, 0 skipped).

## v0.3.10 audit (PRs #252–#258, fixed in #259)

Reviewed after the 0.3.10 merge on `main` @ `60cf6ec`. All items fixed on `fix/autodj-0.3.10-audit` with regression tests in `tests/test_audit_0310.py`; full suite 711 passed.

| ID | Severity | Location | Finding | Status |
|----|----------|----------|---------|--------|
| F-010 | Critical | `autodj/__main__.py` `_auto_discover` | Corrupted-cache cleanup ran `rmtree(dirname(comtypes.client._generate.__file__))` = `site-packages/comtypes/client` (verified on host) on any auto-discover error containing "SyntaxError" | FIXED — `_clean_comtypes_gen_cache()` removes only generated `*.py` (not `__init__.py`) and `__pycache__` in `comtypes.client.gen_dir` |
| F-011 | High | `installer.nsi` SEC_MPV / Uninstall | mpv installed to `$APPDATA\mpv` (mpv's per-user config folder); uninstall `RMDir /r` deleted user `mpv.conf`/scripts; also contradicted `--write-install-paths` (`<install>\mpv\mpv.exe`) so fresh installs could not find mpv | FIXED — back to `$INSTDIR\mpv`; example `mpv_path = "mpv/mpv.exe"` |
| F-012 | High | `scripts/{nsis,mpv,pyinstaller}-check.ps1` | NSIS check never failed; `Test-Path "mpv.exe"` checked CWD not PATH; `MPV_BUNDLE_EXE` dropped; `$(PY)` ran the `py` launcher and always reported OK; stray `\win11-check-.log` | FIXED — `Get-Command`, NSIS exits 1, `-BundleExe`/`-Python` passed by Makefile; `make win11-check` VERIFIED on Windows 11 |
| F-013 | Medium | `autodj/engine.py` `_is_mic_notice` | Keyword substring fallback: any chat containing "is the dj"/"กำลังพูด" announced its sender as DJ | FIXED — whole-line `<nick> <phrase>` only, sender must equal the named nick |
| F-014 | Medium | `autodj/engine.py` `_remember_sent` | Idempotent remember + consuming `_is_echo` let the 2nd echo of a repeated line through as a real message (could reach AI) | FIXED — one entry per post; `say()` no longer double-remembers |
| F-015 | Low | `config.py`, `config.example.toml`, `gui.py` | `mic_greeting_message` unused; `mic_greeting_*` missing from example/Settings; hard-coded Thai fallback | FIXED |
| F-016 | Low | version files | `__init__.py`, `installer.nsi`, `version_info.txt`, `install.bat` still 0.3.9 (3 version tests failed on main) | FIXED |
| F-017 | Medium | `scripts/build_installer.ps1` | `make installer` packaged a stale `dist\config.toml` from the last `build.ps1` run | FIXED — re-stages `config.example.toml` every run; installer compiled (0.3.10) on Windows 11 |

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

