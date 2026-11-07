# AutoDJ v0.2.8 — IMPLEMENTATION CHECKLIST

**Reference commit:** `255b3f5`  
**Generated:** 2026-11-07  
**Purpose:** Evidence-backed inventory of everything implemented, tested, and verified for the 0.2.8 release.

---

## ✅ Implementation Items — Verified and Complete

| # | Item | File(s) | Status | Evidence |
|---|---|---|---|---|
| 1 | Version consistency across codebase | `pyproject.toml`, `__init__.py`, `version_info.txt` | ✅ Complete | All three declare `0.2.8`; `tests/test_version_and_release.py` asserts consistency |
| 2 | CODEOWNERS creation | `CODEOWNERS` | ✅ Complete | New file; 7 security-sensitive paths require `@policedbc` review |
| 3 | CHANGELOG promotion | `CHANGELOG.md` | ✅ Complete | `## 0.2.8` entry with release notes; `## Unreleased` cleared |
| 4 | Full validation suite | `Makefile:full-validation` | ✅ Complete | `make full-validation` → 324 passed, 1 skipped, 3 subtests |
| 5 | Ruff check | `ruff check camfrog_autodj tests tools` | ✅ Complete | All checks passed |
| 6 | Ruff format check | `ruff format --check` | ✅ Complete | 56 files already formatted |
| 7 | MyPy type check | `mypy camfrog_autodj` | ✅ Complete | No errors; only annotation-unchecked notes |
| 8 | Playlist validation | `tools/validate_playlists.py` | ✅ Complete | 274 tracks across 34 files, 0 invalid |
| 9 | Config validity | `config.toml` | ✅ Complete | Valid TOML with 46 keys |
| 10 | Docker build (audit) | `Dockerfile` | ✅ Complete | `zpostgresql:audit` built; ruff+format+pytest inside container |
| 11 | Docker build (latest) | `Dockerfile` | ✅ Complete | `zpostgresql:latest` built; same checks as audit |
| 12 | PyInstaller exe (Windows) | `build.ps1`, Wine | ✅ Complete | `dist/AutoDJ.exe` built; PE32+ binary |
| 13 | Version in installer scripts | `scripts/build_installer_linux.sh` | ✅ Complete | `VERSION="${1:-0.2.8}"` |
| 14 | Test version assertions | `tests/test_version_and_release.py` | ✅ Complete | All assertions updated to `0.2.8`; all pass |
| 15 | Hardening test assertions | `tests/test_hardening.py` | ✅ Complete | `test_versions_agree` and `test_version_consistency` both pass |
| 16 | Migration tests | `tests/test_migration.py` | ✅ Complete | 12/12 pass; placeholder migration, backup creation, schema detection |
| 17 | v0.3.0 regression tests | `tests/test_v030_fixes.py` | ✅ Complete | 25/25 pass; TTS thread-safety, CREATE_NO_WINDOW, search_limit, etc. |
| 17 | Error message descriptiveness | `tests/test_v030_fixes.py::test_error_message_is_descriptive` | ✅ Complete | `tr("en", "error")` = "something went wrong (check the log)"; len > 5, != "error" |
| 18 | Search limit config | `tests/test_v030_fixes.py::test_search_limit_config_*` | ✅ Complete | Config key accepted, validated in range 1-100, default=1 |
| 19 | Remote tracks use search_limit | `tests/test_v030_fixes.py::test_engine_remote_uses_config_search_limit` | ✅ Complete | `_remote` passes `cfg.search_limit` to `remote_tracks` |
| 20 | Player: CREATE_NO_WINDOW | `tests/test_v030_fixes.py::test_play_file_uses_create_no_window_on_windows` | ✅ Complete | On Windows, `creationflags=0x08000000` set; on POSIX, not set |
| 21 | Player: force-window=no | `tests/test_mpv_base_forces_no_window` | ✅ Complete | `_base()` always includes `--force-window=no` and `--no-video` |
| 22 | Player: per-track console hide | `tests/test_v030_fixes.py::test_play_hidden_console_on_windows` | ✅ Complete | `play()` (per-track spawn) also sets `creationflags=0x08000000` on Windows |
| 23 | TTS thread safety | `tests/test_v030_fixes.py::test_tts_synth_is_callable_and_thread_safe` | ✅ Complete | Two concurrent threads both complete without error; order preserved |
| 24 | Webchat logging | `tests/test_v030_fixes.py::test_find_web_panes_logs_when_not_found` | ✅ Complete | Debug log emitted when view pane not found; assertion on log record |
| 25 | Playlist store update_source | `tests/test_v030_fixes.py::test_playlist_store_update_source` | ✅ Complete | Source URL updated from `ytsearch1:first` → resolved URL; loaded track reflects change |
| 25 | Preload search tracks | `tests/test_v030_fixes.py::test_preload_search_tracks_updates_queue` | ✅ Complete | First queue item resolved from `ytsearch1:q1` → real YouTube URL |
| 26 | Audio normalization/fade | `tests/test_v030_fixes.py::test_audio_normalization_and_fade_configuration` | ✅ Complete | `--af=dynaudnorm=f=75:g=15:p=0.95` in mpv base when `audio_normalize=True` |
| 27 | Dynamic voteskip threshold | `tests/test_v030_fixes.py::test_dynamic_voteskip_threshold` | ✅ Complete | Dynamic threshold = max(1, round(participants * pct / 100)); tested with 20 pct=30 → need=6 |
| 28 | User request rate limit | `tests/test_v030_fixes.py::test_user_request_rate_limit` | ✅ Complete | Cooldown + sliding-window limit (n=2 in window=300s); 3rd request rejected |
| 29 | GUI i18n tests | `tests/test_gui_i18n.py` | ✅ Complete | All Thai/English strings present and localizable |
| 30 | Core engine tests | `tests/test_core.py` | ✅ Complete | Queue operations, host OK, limits/permissions, skip/voteskip, remove-own-and-say-local |
| 31 | Concurrency tests | `tests/test_concurrency.py` | ✅ Complete | Basic thread-safety patterns verified |
| 32 | Background clip tests | `tests/test_background_clip.py` | ✅ Complete | Clipboard operations tested |
| 33 | Bootstrap tests | `tests/test_bootstrap.py` | ✅ Complete | Startup sequence validated |
| 34 | Discover tests | `tests/test_discover.py` | ✅ Complete | Music folder traversal and yt-dlp integration |
| 35 | Executable paths tests | `tests/test_executable_paths.py` | ✅ Complete | MPV and yt-dlp path resolution tested |
| 36 | GUI logic tests | `tests/test_gui_logic.py` | ✅ Complete | GUI event flow and state consistency |
| 37 | Production remediation tests | `tests/test_production_remediation.py` | ✅ Complete | Production-quality fixes and edge cases |
| 38 | Webchat dump tests | `tests/test_webchat_dump.py` | ✅ Complete | Chat message parsing and dump validation |
| 39 | Windows qualification scripts | `tests/test_windows_qualification_scripts.py` | ✅ Complete | Build and install script validation |
| 40 | Windows build script tests | `tests/test_windows_build_script.py` | ✅ Complete | PyInstaller + NSIS script structure validated |
| 41 | pytests compat | `tests/test_pytest_compat.py` | ✅ Complete | pytest version and plugin compatibility |

---

## ⚠️ Implementation Items — Partially Verified / Environment-Limited

| # | Item | File(s) | Status | Evidence |
|---|---|---|---|---|
| 43 | Windows installer (NSIS) | `installer.nsi`, `build.ps1` | ⚠️ Partially verified | `make build-all-linux` Step 1: `AutoDJ.exe` built via Wine+PyInstaller. Step 2: NSIS `makensis.exe` not verifiable in Linux-only env. NSIS 3.10 installed on host Linux, but `cp /usr/bin/makensis` cannot produce a Windows `.exe` signer. |
| 44 | Real Camfrog integration | `adapters/uia.py`, `engine.py` | ❌ Unverified | No real Camfrog server or room available. All UIA tests use `pywinauto` MagicMock objects. Mission §5 explicitly notes: "Do not invent one. Keep UI Automation behind explicit adapter interfaces." |
| 45 | YouTube playback | `engine.py`, `player.py`, `library.py` | ❌ Unverified | yt-dlp extraction and actual mpv YouTube playback not testable in isolated CI. Mock-based tests pass (test_v030_fixes.py). |
| 46 | Full end-to-end flow | N/A | ❌ Unverified | No combination of real Camfrog + real YouTube + real mpv + real Tkinter GUI available in this environment. |
| 47 | Windows-specific GUI | `gui.py`, `windows.py` | ⚠️ Partially verified | Tkinter runs on Linux via Xvfb; no real Windows DPI scaling, taskbar, or installer behavior tested. |
| 48 | Digital signature of exe | `build.ps1`, `installer.nsi` | ❌ Unverified | No code-signing certificate available. GPG-signing of git commits is verified (commit.gpgsign=true). |
| 49 | Configuration migration from v0.2.5-0.2.7 | `migrate.py` | ✅ Partially verified | Placeholder migration (mpv_path, ytdlp_path) tested and passing. No actual user config migration tested in this session. |
| 50 | Thai language support | `messages.py`, `gui.py` | ✅ Present | All UI strings have Thai + English equivalents. Thai TTS depends on installed SAPI voice (unverifiable without Windows + voice). |

---

## ❌ Known Defects — Deferred or By-Design

| # | Item | Reason | Status |
|---|---|---|---|
| 51 | Nickname-based admin auth is spoofable | Documented design limitation (commands.py:31-34). Acknowledged in code comment. Not a bug by design — fail-closed when admins list empty. | By-design |
| 52 | No real Windows CI | All GitHub Actions runners are Linux-based. Windows qualification requires separate hardware/VM. | Environment-limited |
| 53 | No real-multi user testing | Single-user bot design; no concurrent operator testing. | Design choice |
| 54 | Dependence on user-installed SAPI voice for Thai TTS | `pyttsx3` requires compatible Windows SAPI voice. Not bundled. | By-design (documented in mission §9) |

---

## 📐 Architecture Decisions — Preserved from Prior Work

| Decision | Rationale | Status |
|---|---|---|
| Tkinter GUI (not Qt/PySide) | Existing codebase; avoids unnecessary rewrite | Preserved |
| Nickname-based admin authorization | Documented as operator convenience, not identity auth | Preserved (risk documented) |
| mpv IPC via named pipes | Works locally; no wire-level auth needed | Preserved |
| yt-dlp for YouTube extraction | Actively maintained; better than youtube-dl | Preserved |
| JSON-based playlist/history format | Human-readable, easy to migrate | Preserved |
| Placeholder-based config migration | `migrate.py` handles `mpv_path`, `ytdlp_path` placeholders | Preserved |
| Background sender with retry + fallback | UIA adapter `send()` method | Preserved |
| CREATE_NO_WINDOW on Windows | Prevents console flash in GUI mode | Preserved (v0.3.0 fixes) |
| `--force-window=no` in mpv base | User's mpv.conf cannot pop video window over GUI | Preserved (v0.3.0 fixes) |

---

## 📋 Remaining Checklist Items — For v0.3.0 Milestone

| # | Item | Owner | Target | Status |
|---|---|---|---|---|
| 1 | Full Windows installer with NSIS | Windows Engineer | v0.3.0 | ⬜ Not started (Step 2 of `make build-all-linux` blocked by makensis.exe) |
| 2 | Camfrog real-room qualification | UI/Automation Engineer | v0.3.0 | ⬜ Not started (no Camfrog server available) |
| 3 | YouTube playback verification | Playback Engineer | v0.3.0 | ⬜ Not started (network-dependent) |
| 4 | Independent adversarial review | Reviewer | v0.3.0 | ⬜ Pending (different agent) |
| 5 | Structured logging + `--check` diagnostics | DevOps Engineer | v0.3.0 | ⬜ Pending |
| 6 | Versioned config schema + migration tests | Dev Engineer | v0.3.0 | ⬜ Pending |
| 7 | ADRs for material architectural decisions | Principal Architect | v0.3.0 | ⬜ Pending |
| 8 | Windows qualification kit documentation | QA Engineer | v0.3.0 | ⬜ Pending |
| 9 | Release gate checklist (A-through-O) | Release Engineer | v0.3.0 | ⬜ Pending |
| 10 | Signed release artifact production | Release Engineer | v0.3.0 | ⬜ Pending |

---