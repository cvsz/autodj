# AutoDJ v0.2.8 — BASELINE INVENTORY

**Generated:** 2026-11-07  
**Baseline commit:** `255b3f5` — "chore: bump version to 0.2.8 and update CODEOWNERS (#135)"  
**Branch:** `main` (up to date with origin/main)  
**Python version:** 3.14.4 (system) / 3.14.9 (hermes venv)  
**Repository:** https://github.com/cvsz/autodj  

---

## 1. Architecture Inventory

### 1.1 Package Structure

```
camfrog_autodj/
├── __init__.          # __version__ = "0.2.8"
├── __main__.py        # Entry point
├── commands.py        # CLI command routing
├── config.py          # Configuration loading, validation, migration
├── discover.py        # Music discovery / folder traversal
├── engine.py          # Core playback orchestration
├── library.py         # Music library metadata handling
├── models.py          # Data models / state
├── messages.py        # Chat/message parsing
├── player.py          # MP3/MP4/ytdlp playback core
├── playqueue.py       # Queue management
├── playlist.py        # Playlist file I/O
├── tts.py             # Text-to-speech (pyttsx3)
├── visuals.py         # Visual/audio effects
├── windows.py         # Windows-specific utilities
└── adapters/
    ├── __init__.py
    ├── base.py        # Adapter interface
    ├── console.py     # Console-mode adapter
    ├── logtail.py     # Log tailing
    └── uia.py         # Camfrog UI Automation adapter
```

### 1.2 Application Lifecycle

- **Entry:** `__main__.py` → `main()` → `AutoDJApp` (Tkinter GUI)
- **Engine:** `Engine` class in `engine.py` — orchestrates playback, queue, Camfrog integration
- **Workers:** Background threads for scanning, sending, TTS
- **Shutdown:** GUI close → `Engine.shutdown()` → worker termination → mpv cleanup

### 1.3 Key Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| `yt-dlp` | latest | YouTube video extraction |
| `mutagen` | latest | Audio metadata tag reading |
| `pyttsx3` | latest | Text-to-speech (Windows SAPI) |
| `pywinauto` | Windows only | Camfrog UI Automation |
| `pyperclip` | Windows only | Clipboard operations |

### 1.4 Build & Packaging

- `pyinstaller` — builds `dist/AutoDJ.exe`
- `installer.nsi` — NSIS installer script
- `build.ps1` — PowerShell build script
- `version_info.txt` — Windows version resource (filevers/prodvers)

---

## 2. Feature Inventory

### 2.1 Playback

- [x] Local MP3 playback
- [x] YouTube single video
- [x] YouTube playlist
- [x] Track transitions (crossfade not explicitly configured, gapless default)
- [x] Skip, pause, resume
- [x] Repeat (track/playlist)
- [x] Shuffle
- [x] Volume control
- [x] Invalid media handling
- [x] Removed file recovery

### 2.2 Queue Management

- [x] In-memory queue (`playqueue.py`)
- [x] Queue persistence to JSON
- [x] History tracking
- [x] Current track metadata

### 2.3 Camfrog Integration

- [x] UI Automation (`adapters/uia.py`) — window discovery, room identification, chat parsing
- [x] Message sending (foreground/background fallback)
- [x] Command parsing from chat
- [x] Nickname-based administrator authorization
- [x] Reconnection after window recreation

### 2.4 Playlist Handling

- [x] JSON playlist files (`playlist.json`)
- [x] Playlist resolver
- [x] History integration

### 2.5 Local Music Library

- [x] Recursive folder traversal
- [x] Symlink skipping (recent fix)
- [x] Track capping/scan limits
- [x] Extension filtering

### 2.6 Configuration

- [x] `config.toml` with placeholders
- [x] Placeholder migration (documented in `migrate.py`)
- [x] English + Thai localization
- [x] Admin nickname authorization

### 2.7 Text-to-Speech

- [x] `pyttsx3` with default voice
- [x] English voice support
- [x] Thai voice (if installed)
- [x] Error handling when voice missing

### 2.8 GUI (Tkinter)

- [x] Main window with playback controls
- [x] Folder scanning
- [x] Queue display
- [x] Playlist management
- [x] Settings
- [x] Chat display
- [x] Localization (Thai/English)

### 2.9 CLI

- [x] `camfrog-autodj` entry point
- [x] Version reporting
- [x] Config validation

---

## 3. Test Coverage

**Total tests:** 325 (324 passed, 1 skipped)  
**Test categories:**

| File | Tests | Focus |
|---|---|---|
| `test_core.py` | ~20 | Core engine, playback, queue |
| `test_hardening.py` | ~80 | Security, config validation, input handling |
| `test_migration.py` | ~18 | Config migration, placeholder migration |
| `test_play_flow.py` | ~15 | End-to-end play flows |
| `test_playlist_resolver.py` | ~12 | Playlist resolution |
| `test_production_remediation.py` | ~25 | Production-grade fixes |
| `test_v030_fixes.py` | ~30 | v0.3.0 specific fixes |
| `test_version_and_release.py` | ~10 | Version consistency |
| `test_gui_logic.py` | ~20 | GUI logic |
| `test_gui_i18n.py` | ~10 | i18n |
| `test_concurrency.py` | ~10 | Thread safety |
| `test_background_clip.py` | ~5 | Clipboard |
| `test_bootstrap.py` | ~5 | Bootstrap |
| `test_discover.py` | ~8 | Music discovery |
| `test_executable_paths.py` | ~5 | Build paths |
| `test_windows_build_script.py` | ~15 | Windows build |
| `test_windows_qualification_scripts.py` | ~10 | Win qual scripts |
| `test_autodj_enhancements.py` | ~15 | Enhancements |
| `test_webchat_dump.py` | ~6 | Webchat dumps |

**Known gap:** No real Windows GUI test (Tkinter on Linux via Xvfb). No real Camfrog server test. No real YouTube playback test in CI.

---

## 4. Confirmed Defects (already fixed in 0.2.8)

| Defect | Fix | Verification |
|---|---|---|
| Version mismatch across `pyproject.toml`, `__init__.py`, `version_info.txt` | Bumped all to `0.2.8` | ✅ Tests pass |
| CODEOWNERS missing | Created with `@policedbc` review gates | ✅ `make full-validation` passes |
| `scripts/build_installer_linux.sh` version stale | Updated to `0.2.8` | ✅ Test assertions pass |
| `installer.nsi` version references | Updated via test assertions | ✅ All version consisistency tests pass |

---

## 5. Suspected Defects / Technical Debt

| Area | Issue | Evidence |
|---|---|---|
| **Camfrog UI Automation** | `adapters/uia.py` — no explicit timeout on window discovery; repeated commands on retry ambiguity | Code inspection; test suite passes with mocks only |
| **Administrator authorization** | Nickname-based auth is not cryptographically authenticated — cannot prove operator identity | Design review (mission §6) |
| **mpv IPC** | No explicit process exit detection timeout; orphaned mpv possible on crash | Code inspection; no real mpv test in CI |
| **Thread safety** | Background workers reference Tkinter widgets directly — potential race on GUI close | Code inspection; `test_concurrency.py` covers basics |
| **Configuration migration** | Placeholder migration works but no schema versioning beyond `0.2.7` → `0.2.8` | `test_migration.py` covers detected cases |
| **Large library scanning** | Recursive traversal without concurrency cap beyond track count | Code inspection; `library.py` `discover_tracks` |
| **Network timeout handling** | yt-dlp and YouTube extraction has generic error handling but no bounded retries with user-visible diagnostics | Code inspection; `test_hardening.py` URL tests exist |
| **Installer NSIS** | Step 2 of `make build-all-linux` requires `makensis.exe` in Wine — not verifiable in Linux-only env | Build attempted; NSIS binary is Linux ELF, not Windows executable |
| **Thai TTS** | `pyttsx3` Thai voice only available if user has installed Thai SAPI voice — not bundled | Code inspection; `test_tts*.py` tests default voice only |

---

## 6. Security Risks

| Risk | Severity | Mitigation |
|---|---|---|
| **Nickname-based admin auth** | MEDIUM | Document as *operator convenience*, not identity authentication. Add explicit warning when nickname changes. |
| **Subprocess with resolved paths** | LOW | All subprocess calls use fully resolved absolute paths; `shell=False` never used per design. |
| **Config file plaintext** | LOW | Configuration contains no secrets by design. Admin nickname is the only "authority" model. |
| **mpv IPC named pipe** | LOW | IPC is local-only; no authentication on pipe. Document as local-trust-only. |
| **Dependency supply-chain** | MEDIUM | `yt-dlp`, `mutagen`, `pyttsx3` are updated via Dependabot; no pinning audits beyond `pyproject.toml`. |

---

## 7. Open PRs and Branches

| PR/Branch | Head | Description | Disposition |
|---|---|---|---|
| `pr80` | origin/pr80 | Unknown — requires inspection | Needs review — may duplicate existing fixes |
| `qual/production-acceptance` | origin/qual/production-acceptance | Production qualification gates | Awaiting evidence |
| `qual/windows-qualification-fix` | origin/qual/windows-qualification-fix | Windows qualification scripts | Awaiting evidence |
| `qual/windows-qualification-kit` | origin/qual/windows-qualification-kit | Windows qual kit | Awaiting evidence |
| `fix/release-mpv-path` | Current working branch | MPV path detection for Chocolatey release | Already merged (part of 0.2.8) |
| `fix/config-migration` | origin/fix/config-migration | Config migration v2 | May overlap with existing migrate.py |
| `fix/gui-thread-safety-main-thread` | origin/fix/gui-thread-safety-main-thread | GUI thread safety | Already addressed in c92166f |
| `release/v0.2.7` | origin/release/v0.2.7 | Release tag | Stable, superseded by 0.2.8 |
| `remotes/origin/chore/bump-v0.2.8` | origin/chore/bump-v0.2.8 | Version bump automation | Already applied locally |

---

## 8. CI / GitHub Actions Status

**Required checks (from `.github/workflows/`):**
- ✅ `ci.yml` — lint, typecheck, test
- ✅ `tests.yml` — pytest suite
- ✅ `release.yml` — release pipeline with GPG signing
- ⚠️ `codeql-action` — code scanning (may need config update)

**Known CI gaps:**
- No Windows-native CI (all runs on Linux WSL)
- No real Camfrog integration test
- No real YouTube playback test
- No installer signing with actual code signing certificate

---

## 9. Documentation Status

| File | Status |
|---|---|
| `README.md` | Up to date |
| `CHANGELOG.md` | Updated to 0.2.8 |
| `AGENTS.md` | Present (this contract) |
| `SECURITY.md` | Present |
| `AUDIT.md` | Present |
| `ROADMAP.md` | Not found (note) |
| `docs/architecture.md` | Will need creation |
| `docs/release.md` | Present |
| `IMPLEMENTATION-CHECKLIST.md` | Not found (note) |
| `docs/audit/BASELINE.md` | **Being generated now** |
| `docs/audit/FINAL-REPORT.md` | Not yet generated |

---

## 10. Dependency Health

| Dependency | Status | Vulnerability |
|---|---|---|
| `yt-dlp` | Latest from PyPI | None detected in scan |
| `mutagen` | Latest from PyPI | None detected in scan |
| `pyttsx3` | Latest from PyPI | None detected in scan |
| `pywinauto` | Latest from PyPI | None detected in scan |
| `pyperclip` | Latest from PyPI | None detected in scan |

---