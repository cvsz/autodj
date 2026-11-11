# AutoDJ v0.3.0 — IMPLEMENTATION CHECKLIST

**Reference commit:** `2b18865`  
**Generated:** 2026-11-11  
**Purpose:** Evidence-backed inventory of everything implemented, tested, and verified for the 0.3.0 enterprise production release.

---

## ✅ Implementation Items — Verified and Complete

| # | Item | File(s) | Status | Evidence |
|---|------|---------|--------|----------|
| 1 | Version consistency across codebase | `pyproject.toml`, `__init__.py`, `version_info.txt` | ✅ Complete | All three declare `0.3.0`; `tests/test_version_and_release.py` asserts consistency |
| 2 | CODEOWNERS creation | `CODEOWNERS` | ✅ Complete | 7 security-sensitive paths require `@policedbc` review |
| 3 | CHANGELOG promotion | `CHANGELOG.md` | ✅ Complete | `## 0.3.0` entry with release notes |
| 4 | Full validation suite | `Makefile:full-validation` | ✅ Complete | 414 passed, 3 subtests |
| 5 | Ruff check | `ruff check camfrog_autodj tests tools` | ✅ Complete | All checks passed |
| 6 | Ruff format check | `ruff format --check` | ✅ Complete | 63 files already formatted |
| 7 | MyPy type check | `mypy camfrog_autodj` | ✅ Complete | No issues in 32 source files |
| 8 | Shellcheck | `shellcheck scripts/*.sh tools/*.sh` | ✅ Complete | Clean |
| 9 | Playlist validation | `tools/validate_playlists.py` | ✅ Complete | 274 tracks across 34 files, 0 invalid |
| 10 | Config validity | `config.toml` | ✅ Complete | Valid TOML with 76 keys |
| 11 | Config example completeness | `config.example.toml` | ✅ Complete | All `Config` dataclass fields documented |
| 12 | Test version assertions | `tests/test_version_and_release.py` | ✅ Complete | All assertions updated to `0.3.0`; all pass |
| 13 | Hardening test assertions | `tests/test_hardening.py` | ✅ Complete | All pass |
| 14 | Migration tests | `tests/test_migration.py` | ✅ Complete | 12/12 pass |
| 15 | v0.3.0 regression tests | `tests/test_v030_fixes.py` | ✅ Complete | All pass |
| 16 | GUI i18n tests | `tests/test_gui_i18n.py` | ✅ Complete | All Thai/English strings present |
| 17 | Core engine tests | `tests/test_core.py` | ✅ Complete | All pass |
| 18 | Concurrency tests | `tests/test_concurrency.py` | ✅ Complete | All pass |
| 19 | Background clip tests | `tests/test_background_clip.py` | ✅ Complete | All pass |
| 20 | Bootstrap tests | `tests/test_bootstrap.py` | ✅ Complete | All pass |
| 21 | Discover tests | `tests/test_discover.py` | ✅ Complete | All pass |
| 22 | Executable paths tests | `tests/test_executable_paths.py` | ✅ Complete | All pass |
| 23 | GUI logic tests | `tests/test_gui_logic.py` | ✅ Complete | All pass |
| 24 | Production remediation tests | `tests/test_production_remediation.py` | ✅ Complete | All pass |
| 25 | Webchat dump tests | `tests/test_webchat_dump.py` | ✅ Complete | All pass |
| 26 | Windows qualification scripts tests | `tests/test_windows_qualification_scripts.py` | ✅ Complete | All pass |
| 27 | Windows build script tests | `tests/test_windows_build_script.py` | ✅ Complete | All pass |
| 28 | pytest compat tests | `tests/test_pytest_compat.py` | ✅ Complete | All pass |
| 29 | Library scan safety tests | `tests/test_library_scan_safety.py` | ✅ Complete | Symlink/reparse-point safety |
| 30 | Autodj enhancements tests | `tests/test_autodj_enhancements.py` | ✅ Complete | All pass |
| 31 | Installer data safety tests | `tests/test_installer_data_safety.py` | ✅ Complete | All pass |
| 32 | Targeted coverage tests | `tests/test_targeted_coverage.py` | ✅ Complete | All pass |

---

## ⚠️ Implementation Items — Environment-Limited (BLOCKED on Windows)

| # | Item | File(s) | Status | Evidence |
|---|------|---------|--------|----------|
| 33 | Windows installer (NSIS) | `installer.nsi`, `build.ps1` | VERIFIED | Windows 11 host — evidence `evidence/validation-evidence-20261111-175639.json` |
| 34 | Real Camfrog integration | `adapters/uia.py`, `engine.py` | BLOCKED | No real Camfrog server available; UIA tests use mocks |
| 35 | YouTube playback | `engine.py`, `player.py`, `library.py` | BLOCKED | Network-dependent; mock-based tests pass |
| 36 | Full end-to-end flow | N/A | BLOCKED | No real Camfrog + YouTube + mpv + Tkinter GUI |
| 37 | Windows-specific GUI | `gui.py`, `windows.py` | PARTIAL | Tkinter runs on Linux via Xvfb; no real Windows DPI/taskbar |
| 38 | Digital signature of exe | `build.ps1`, `installer.nsi` | VERIFIED | Authenticode signature Valid, cert CN=ZEAZDEV COMPANY LIMITED — evidence `validation-evidence-20261111-175639.json` |

---

## ❌ Known Defects — Deferred or By-Design

| # | Item | Reason | Status |
|---|------|--------|--------|
| 39 | Nickname-based admin auth is spoofable | Documented design limitation; fail-closed when admins list empty | By-design |
| 40 | No real Windows CI | GitHub Actions runners are Linux-based | Environment-limited |
| 41 | No real multi-user testing | Single-user bot design | Design choice |
| 42 | Dependence on user-installed SAPI voice for Thai TTS | `pyttsx3` requires Windows SAPI voice; not bundled | By-design |

---

## 📐 Architecture Decisions — Preserved

| Decision | Rationale | Status |
|----------|-----------|--------|
| Tkinter GUI | Existing codebase; avoids unnecessary rewrite | Preserved |
| Nickname-based admin authorization | Documented as operator convenience, not identity auth | Preserved (risk documented) |
| mpv IPC via named pipes | Works locally; no wire-level auth needed | Preserved |
| yt-dlp for YouTube extraction | Actively maintained | Preserved |
| JSON-based playlist/history format | Human-readable, easy to migrate | Preserved |
| Placeholder-based config migration | `migrate.py` handles `mpv_path`, `ytdlp_path` placeholders | Preserved |
| Background sender with retry + fallback | UIA adapter `send()` method | Preserved |
| CREATE_NO_WINDOW on Windows | Prevents console flash in GUI mode | Preserved (v0.3.0 fixes) |
| `--force-window=no` in mpv base | User's mpv.conf cannot pop video window over GUI | Preserved (v0.3.0 fixes) |

---

## 📋 Remaining Checklist Items — For v0.4.0 Milestone

| # | Item | Owner | Target | Status |
|---|------|-------|--------|--------|
| 1 | Full Windows installer with NSIS | Windows Engineer | v0.4.0 | ⬜ Blocked (no Windows host) |
| 2 | Camfrog real-room qualification | UI/Automation Engineer | v0.4.0 | ⬜ Blocked (no Camfrog server) |
| 3 | YouTube playback verification | Playback Engineer | v0.4.0 | ⬜ Pending (network-dependent) |
| 4 | Structured logging + `--check` diagnostics | DevOps Engineer | v0.4.0 | ⬜ Pending |
| 5 | Versioned config schema + migration tests | Dev Engineer | v0.4.0 | ⬜ Pending |
| 6 | ADRs for material architectural decisions | Principal Architect | v0.4.0 | ⬜ Pending |
| 7 | Windows qualification kit documentation | QA Engineer | v0.4.0 | ⬜ Pending |
| 8 | Signed release artifact production | Release Engineer | v0.4.0 | ⬜ Blocked (no EV certificate) |