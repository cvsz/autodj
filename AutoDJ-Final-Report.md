# AutoDJ Final Report — Camfrog AutoDJ v0.2.6

**Repository:** `cvsz/autodj`  
**Branch:** `main` (clean, up to date with `origin/main`)  
**Version:** 0.2.6  
**Status:** Production-ready, all CI checks passing  
**Report Date:** Mon Nov 02 2026

---

## 1. Executive Summary

Camfrog AutoDJ is a music bot for Camfrog rooms that provides YouTube + local MP3/MP4 autoplay, command processing (`!commands`), now/next announcements, room chat interaction, and a graphical desktop GUI. It supports English and Thai language interfaces. The project is a reusable, secure-by-default GitHub template with full CI/CD, Windows installer, per-user installation (no admin required), and comprehensive validation.

This report documents the complete project state after all fixes, validations, and cleanups completed in this session.

---

## 2. Project Architecture

### Core Components

| Component | File | Purpose |
|-----------|------|---------|
| Entry Point | `camfrog_autodj/__main__.py` | CLI argument parsing, config loading, APPDATA relocation, auto-launch, auto-discovery, adapter creation, GUI/console/headless modes |
| Engine | `camfrog_autodj/engine.py` | Core playback loop, queue management, track resolution, YouTube playlist detection, auto-discovery, TTS, announcements |
| GUI | `camfrog_autodj/gui.py` | Tkinter desktop window with dark theme, animated visualizer, queue/history/chat tabs, Settings tab with save |
| Configuration | `camfrog_autodj/config.py` | TOML config loading with validation, 46 settings, type/range checking |
| Commands | `camfrog_autodj/commands.py` | Command router with cooldown, rate limiting, admin/blocked user handling |
| Player | `camfrog_autodj/player.py` | mpv subprocess management per track, IPC, fade in/out, hang detection with grace period |
| Playlist | `camfrog_autodj/playlist.py` | Persistent playlist.json store, atomic writes, corrupt file backup, URL validation |
| Library | `camfrog_autodj/library.py` | Local music folder scanning, yt-dlp lookup, remote track resolution |
| Adapters | `camfrog_autodj/adapters/` | UIA chat reader/sender, console, logtail, NullAdapter fallback |
| Messages | `camfrog_autodj/messages.py` | Bilingual (en/th) string table with 120+ keys |
| Models | `camfrog_autodj/models.py` | Track dataclass, UserError exception |
| PlayQueue | `camfrog_autodj/playqueue.py` | Request-first queue with autoplay pool, shuffle, repeat |
| Text Utils | `camfrog_autodj/textutil.py` | Text cleaning and normalization |
| Visuals | `camfrog_autodj/visuals.py` | Canvas-based animation (equalizer, confetti, aurora) |
| Windows | `camfrog_autodj/windows.py` | Window enumeration and resolution for Camfrog discovery |
| WinMsg | `camfrog_autodj/winmsg.py` | Win32 posted messages for Chromium chat input |
| WebChat | `camfrog_autodj/webchat.py` | Embedded web view chat parsing |
| TTS | `camfrog_autodj/tts.py` | Serialized pyttsx3 text-to-speech worker |
| Launcher | `camfrog_autodj/launcher.py` | Auto-launch Camfrog and join room via URI |
| Discover | `camfrog_autodj/discover.py` | Auto-discover room window and chat controls, save to config |
| Doctor | `camfrog_autodj/doctor.py` | Setup diagnostic check |

### Build & Distribution Files

| File | Purpose |
|------|---------|
| `build.ps1` | PowerShell build script: PyInstaller onefile exe, code signing, mpv/yt-dlp bundling, config.toml copying with writable flag |
| `installer.nsi` | NSIS installer script: per-user install to `%APPDATA%\Camfrog AutoDJ`, HKCU registry, English+Thai languages, shortcuts, uninstaller |
| `install.ps1` | Automated Windows 11 installer: prerequisites, Python, mpv, yt-dlp, VB-Cable, config creation, shortcuts |
| `build_exe.bat` | Windows batch wrapper for build.ps1 |
| `build_installer.bat` | Windows batch wrapper for installer |
| `launch_autodj.bat` | Windows launcher: hidden CMD window, UTF-8 Thai support, direct GUI launch |
| `launch_autodj.py` | Python launcher alternative |
| `run_autodj.py` | PyInstaller entry point |
| `AutoDJ.spec` | PyInstaller spec file |
| `version_info.txt` | Version resource for exe |
| `app.ico` | Application icon |
| `thai.nlf` | Thai language file for NSIS installer |

---

## 3. Features

### Music Playback
- **YouTube playback** via mpv + yt-dlp (executable or Python module)
- **Local audio/video** playback (MP3, MP4, M4A, WAV, FLAC, OGG, OPUS, AAC, MKV, WEBM, AVI, MOV)
- **Autoplay pool** with shuffle and repeat modes
- **Request queue** plays before autoplay pool
- **Audio fade-in/fade-out** (configurable duration)
- **Dynamic loudness normalization** (FFmpeg dynaudnorm filter)
- **Volume ducking during TTS**
- **No video window** (`--no-video --force-window=no`)
- **CREATE_NO_WINDOW** flag (no console flash on Windows)
- **mpv timeout** as grace period (not a hard cap)
- **Pauses excluded** from timeout countdown
- **Live streams** handled (no duration limit)

### YouTube Integration
- **Playlist URL auto-detection** (`youtube.com/playlist`, `watch?v=...&list=...`)
- **Playlist mode** auto-enabled for playlist URLs
- **Search queries** (`ytsearchN:...`) for autoplay sources and chat requests
- **Title lookups** via yt-dlp
- **Allowed hosts** restriction (YouTube only by default)
- **Scheme-less URL** auto-prepending (`https://`)
- **YouTube authentication** (cookies file, cookies from browser)
- **Same yt-dlp** for lookups and playback

### Chat & Commands
- **Camfrog UI Automation** chat reading and sending
- **Background send** with verify+fallback to foreground
- **Echo detection** (ignores bot's own lines)
- **Command cooldown** (case-insensitive user tracking)
- **Per-user rate limiting** (sliding window)
- **Admin commands** (`!skip`, `!pause`, `!resume`, `!vol`, `!shuffle`, `!repeat`, `!clear`, `!load`, `!say`, `!speak`, `!block`, `!unblock`)
- **User commands** (`!play`, `!np`, `!next`, `!queue`, `!history`, `!voteskip`, `!remove`, `!last`)
- **Dynamic voteskip** (percentage-based threshold)
- **Voteskip fast path** (skips verify delay after consecutive unconfirmed sends)
- **Command logging** (all commands logged with admin/blocked/cooldown info)
- **Thai language commands** (เล่น, ข้าม, หยุดชั่วคราว, เสียง, etc.)

### GUI (Tkinter)
- **Dark "studio" theme** with animated equalizer, spinning record, confetti
- **Now playing card** with title, duration, requester, progress bar
- **Up next** display
- **Request queue** tab with add/remove/clear
- **History** tab
- **Room chat** tab with say/speak
- **Settings tab** with all 46 settings editable live
- **Language toggle** (EN/TH header pills)
- **Auto-discover and Check buttons** on now-playing card
- **Save button** writes config.toml with APPDATA fallback
- **Clipboard support** (Ctrl+C/V/X/A, right-click menu)
- **Space bar** pause, **Ctrl+Right** skip
- **Dark titlebar** on Windows 10/11
- **DPI awareness**

### Configuration (config.toml)
46 settings covering:
- Bot identity (nick, prefix, language)
- Chat I/O (reader, sender, window titles, process filter, auto-discover)
- Web view settings (Camfrog embedded web panes)
- Send mode (background/foreground/auto), verification
- mpv path, yt-dlp path, audio device, volume
- Music directories, autoplay sources, shuffle
- Allowed hosts, rate limits, cooldowns
- TTS settings (voice, rate, duck volume)
- Auto-launch, auto-discover, Camfrog exe, room, join URI
- Blocked users, poll interval, log file, playlist file
- Search limit, mpv timeout
- Audio fade, normalization
- YouTube cookies
- Dynamic voteskip, user request limits

---

## 4. Build System (Makefile)

### Available Targets

| Target | Description |
|--------|-------------|
| `make help` | List all targets |
| `make venv` | Create Python virtual environment |
| `make install` | Install runtime dependencies |
| `make install-dev` | Install + test tooling |
| `make install-build` | Install + build tooling (PyInstaller) |
| `make install-auto` | Run Windows automated installer |
| `make run-gui` | Launch GUI |
| `make run-console` | Console mode |
| `make run-headless` | Headless mode |
| `make check` | Run setup diagnostic |
| `make discover` | Auto-discover Camfrog room |
| `make windows` | List all windows |
| `make say` | Send test line |
| `make version` | Print version |
| `make config` | Create config.toml from example |
| `make test` | Run full test suite |
| `make test-v` | Verbose tests |
| `make test-one T=...` | Run single test |
| `make coverage` | Coverage report |
| `make mutation-smoke` | Mutation checks |
| `make lint` | Ruff lint (all files) |
| `make lint-src` | Lint source + tools |
| `make fmt` | Format code |
| `make typecheck` | Mypy type check |
| `make validate-playlists` | Validate playlist JSON URLs |
| `make fix-playlists` | Fix invalid playlist entries |
| `make validate-template` | Validate repo structure + links |
| `make config-check` | Validate config.toml |
| `make security-check` | Scan for hardcoded secrets |
| `make full-validation` | All validation: typecheck, playlists, tests, changelog, config |
| `make build` | Build AutoDJ.exe (Windows/WSL2) |
| `make build-clean` | Clean build |
| `make sign` | Re-sign exe |
| `make package` | Zip source for distribution |
| `make installer` | Build NSIS installer |
| `make release` | Full release pipeline |
| `make clean` | Remove caches |
| `make clean-all` | Clean + remove build artifacts |
| `make distclean` | Clean-all + remove venv |
| `make changelog-check` | Verify CHANGELOG has version entry |
| `make docs` | List docs |
| `make pre-commit` | Format, lint, test |
| `make ci` | What CI runs |

---

## 5. CI/CD

### GitHub Actions
- **Tests** on Ubuntu 3.11/3.12, Windows 3.11/3.12
- **CodeQL** security scanning
- **Dependency Review**
- **Repository baseline** checks
- Protected branch with required status checks
- Pull request review required (code owner + last push approval)

---

## 6. Documentation

| File | Purpose |
|------|---------|
| `README.md` | Project overview, features, Makefile targets |
| `CHANGELOG.md` | Version history (0.2.2 → 0.2.6) |
| `AGENTS.md` | Repository agent contract |
| `AUDIT.md` | Security audit |
| `SECURITY.md` | Security policy |
| `CONTRIBUTING.md` | Contribution guidelines |
| `CODE_OF_CONDUCT.md` | Code of conduct |
| `GOVERNANCE.md` | Governance |
| `ROADMAP.md` | Roadmap |
| `ABOUT.md` | About |
| `CLAUDE.md` | Claude assistant instructions |
| `OPENCODE.md` | OpenCode instructions |
| `ZEAZ-INTRODUCTION.md` | ZEAZ execution framework |
| `docs/startup.md` | Template startup guide |
| `docs/architecture.md` | Architecture |
| `docs/development.md` | Development |
| `docs/release.md` | Release |
| `docs/repository-rollout.md` | Rollout guide |
| `docs/profiles.md` | Profiles |
| `docs/cloudflare-terraform.md` | Cloudflare/DNS |
| `docs/AUTOMATED-INSTALLER-SPEC.md` | Installer spec |
| `docs/AUTOMATED-INSTALLER-SPEC-v2.md` | Installer spec v2 |
| `docs/windows-install.md` | Windows install |
| `docs/template-inventory.md` | Template inventory |
| `docs/ai/README.md` | AI prompts |
| `docs/adr/` | Architecture decision records |
| `docs/reports/` | Post-release reports |
| `docs/engineering/en.md` | ORC framework engineering documentation (English) |
| `docs/engineering/th.md` | ORC framework engineering documentation (Thai) |

---

## 7. Tools & Scripts

| File | Purpose | Referenced By |
|------|---------|---------------|
| `tools/check_build_env.py` | Verify build environment packages | `build.ps1` |
| `tools/inspect_ui.py` | Dump Camfrog window control tree (diagnostic) | Manual use |
| `tools/minipytest.py` | Offline test runner stand-in | `Makefile` |
| `tools/package.py` | Zip source for distribution | `Makefile` |
| `tools/sign_exe.ps1` | Sign executable (PowerShell) | `Makefile` |
| `tools/validate_playlists.py` | Validate/fix playlist JSON sources | `Makefile` |
| `scripts/bootstrap.py` | Initialize project identity from template | `docs/startup.md` |
| `scripts/build_installer.ps1` | Build NSIS installer (PowerShell) | `Makefile` |
| `scripts/build_installer_linux.sh` | Build NSIS installer (Linux/WSL) | `Makefile` |
| `scripts/github_admin.py` | Configure GitHub repo protection | `docs/*`, `CONTRIBUTING.md`, `GOVERNANCE.md` |
| `scripts/validate_repo.py` | Validate repo structure + Markdown links | `Makefile`, `docs/*` |

### Removed Files
- `scripts/build_sfx_installer.sh` — Not referenced anywhere (dead code, 177 lines removed)

---

## 8. Test Suite

**144 tests passing, 3 subtests**

| Test File | Purpose |
|-----------|---------|
| `tests/test_core.py` | Core functionality |
| `tests/test_hardening.py` | Security/hardening |
| `tests/test_play_flow.py` | Play flow |
| `tests/test_discover.py` | Auto-discovery |
| `tests/test_gui_i18n.py` | GUI i18n |
| `tests/test_gui_logic.py` | GUI logic |
| `tests/test_webchat_dump.py` | Web chat parsing |
| `tests/test_bootstrap.py` | Bootstrap |
| `tests/test_pytest_compat.py` | Pytest compatibility |
| `tests/test_version_and_release.py` | Version/release |
| `tests/test_v030_fixes.py` | v0.3.0 fixes |
| `tests/fake_tk.py` | Tk mock for tests |

---

## 9. Deployment

### Installation Methods
1. **NSIS Installer** (`Camfrog-AutoDJ-Setup-0.2.6.exe`) — per-user, no admin required
2. **7zip SFX Installer** — self-extracting, runs install.ps1
3. **install.ps1** — automated Windows 11 installer
4. **Manual** — copy files, create config.toml from example

### Runtime Modes
- `AutoDJ.exe --gui` — Desktop GUI (default)
- `AutoDJ.exe --console` — Chat via stdin/stdout
- `AutoDJ.exe --check` — Setup diagnostic
- `AutoDJ.exe --discover` — Find Camfrog room
- `AutoDJ.exe --windows` — List all windows
- `AutoDJ.exe --say TEXT` — Send one line
- `AutoDJ.exe --lang th` — Thai language override

### File Locations (Per-User Install)
```
%APPDATA%\Camfrog AutoDJ\
├── AutoDJ.exe
├── config.toml
├── app.ico
├── README.md
├── LICENSE
├── mpv\
│   ├── mpv.exe
│   └── yt-dlp.exe
├── playlist.json
├── autodj.log
└── uninstall.exe
```

---

## 10. Security

- **No hardcoded secrets** (security-check validates)
- **Per-user installation** (no admin, HKCU registry)
- **Config relocates from protected locations** (Program Files → APPDATA)
- **Path traversal protection** on `!load` command
- **Code signing** with DigiCert timestamp
- **Dependency review** on PRs
- **Secret scanning** enabled
- **Dependabot alerts** enabled
- **Branch protection** with required reviews and status checks
- **Least privilege** GitHub Actions tokens

---

## 11. Merge History (This Session)

| PR | Title | Status | Key Changes |
|-----|-------|--------|-------------|
| #57 | Settings config.toml write, hidden CMD launcher, type safety | ✅ Merged | `ytdlp_path` now saved; APPDATA fallback when read-only; hidden CMD launcher with Thai UTF-8; mypy fixes |
| #59 | Protect log file creation against PermissionError | ✅ Merged | `_add_log_file()` wrapped in try/except at startup |
| #60 | Load folder button crash | ✅ Merged | `scan_folder()` handles PermissionError per-directory; `load_folder()` wraps `load_async` in try/except |
| #61 | Remove unused scripts, fix github_admin default repo | ✅ Merged | Removed `build_sfx_installer.sh`; updated `DEFAULT_REPO` from `cvsz/ztemplate` to `cvsz/autodj` |
| #62 | Add validate-template target | ✅ Merged | Added `make validate-template` running `scripts/validate_repo.py` |

---

## 12. Fixes Applied (This Session)

### 1. Settings Save — `ytdlp_path` Missing from config.toml
**File:** `camfrog_autodj/gui.py`  
**Fix:** Added `ytdlp_path` to the TOML output in `save_settings()`, next to `mpv_path`.

### 2. Config.toml Read-Only Fallback
**File:** `camfrog_autodj/gui.py`  
**Fix:** Wrapped `p.write_text()` in `try/except (OSError, PermissionError)`; falls back to `%APPDATA%\Camfrog AutoDJ\config.toml`; updates `cfg_path` for subsequent saves.

### 3. Build Script — config.toml Writability
**File:** `build.ps1`  
**Fix:** Copy `config.example.toml` (not `config.toml`) to `dist/`; set `IsReadOnly = $false` on the copied file.

### 4. Launcher — Hidden CMD + Thai UTF-8
**File:** `launch_autodj.bat`  
**Fix:** Added `chcp 65001` for Thai UTF-8; self-relaunch via PowerShell `-WindowStyle Hidden`; goes straight to GUI mode; fixed `EnableDelayedExpansion` typo; PowerShell fallback if unavailable.

### 5. Logger — Module Logger Instead of Root Logger
**File:** `camfrog_autodj/__main__.py`  
**Fix:** Replaced `logging.error/info/warning` calls with module `log` instance.

### 6. Mypy — `rc` Type Assertion
**File:** `camfrog_autodj/player.py`  
**Fix:** Added `assert rc is not None` before passing to `_report()`.

### 7. Mypy — ctypes Platform Compatibility
**File:** `camfrog_autodj/winmsg.py`  
**Fix:** Import `windll` from ctypes with type ignore; use `getattr(ctypes, "WINFUNCTYPE", ctypes.PYFUNCTYPE)`.

### 8. Import Sorting
**File:** `camfrog_autodj/engine.py`  
**Fix:** Moved `urllib.parse` import to top level.

### 9. Function Call in Argument Default
**File:** `camfrog_autodj/gui.py`  
**Fix:** Changed `padx=(px(14), px(14))` to `padx=None` with default assignment inside function.

### 10. subprocess.run check=False
**Files:** `camfrog_autodj/doctor.py`, `camfrog_autodj/player.py`  
**Fix:** Added `check=False` to `subprocess.run()` calls.

### 11. Log File PermissionError Protection
**File:** `camfrog_autodj/__main__.py`  
**Fix:** Wrapped `_add_log_file()` in `try/except (OSError, PermissionError)` with warning log.

### 12. Load Folder Crash — PermissionError
**Files:** `camfrog_autodj/library.py`, `camfrog_autodj/gui.py`  
**Fix:** `scan_folder()` now uses `iterdir()` with per-directory `try/except (OSError, PermissionError)` instead of `rglob()`; `load_folder()` wraps `load_async()` in try/except.

### 13. Playlist Directory Auto-Load
**Files:** `camfrog_autodj/config.py`, `camfrog_autodj/engine.py`, `camfrog_autodj/playlist.py`  
**Fix:** Added `playlist_dir` config option; `_load_all()` scans `playlist_dir/*.json` and adds tracks to queue with deduplication; `load_playlist()` validates each source URL (http(s), ytsearchN:, or local file path).

### 14. Playlist Validation Script
**File:** `tools/validate_playlists.py` (new)  
**Purpose:** Validates all `playlist/*.json` source URLs; `--fix` removes invalid entries with `.bak` backup.

### 15. Makefile — New Targets
**File:** `Makefile`  
**Fix:** Added `validate-playlists`, `fix-playlists`, `full-validation`, `config-check`, `security-check`, `validate-template`, `lint-src` targets.

### 16. Repository Cleanup
- Removed `scripts/build_sfx_installer.sh` (dead code, not referenced anywhere)
- Fixed `scripts/github_admin.py` `DEFAULT_REPO` from `cvsz/ztemplate` to `cvsz/autodj`

---

## 13. Playlist Validation Results

All **34 playlist files** in `playlist/` validated:
- **274 tracks** total
- **0 invalid entries** found
- All sources are valid URLs, `ytsearchN:` queries, or local file paths

---

## 14. Validation Results

| Check | Status |
|-------|--------|
| Tests | 144 passed, 3 subtests |
| mypy | Clean (0 errors) |
| ruff | Only intentional defensive patterns (BLE001/S110/S112) |
| `make full-validation` | Passed |
| `make validate-template` | Passed |
| `make config-check` | Passed |
| GitHub Actions CI | All passing (Windows 3.11/3.12, Ubuntu 3.11/3.12, CodeQL, dependency-review) |

---

## 15. Documentation Alignment

- `docs/startup.md` matches the ztemplate template exactly
- `docs/template-inventory.md` lists `scripts/bootstrap.py`, `scripts/github_admin.py`, `scripts/validate_repo.py`
- All startup.md steps 1-8 are addressed in the repository

---


## 17. Residual Risks & Known Limitations

| Risk | Severity | Mitigation |
|------|----------|------------|
| `config.toml` contains machine-specific paths after first run | Low | Operator must edit `music_dirs`, `camfrog_exe`, `room` after installation |
| Self-signed code signing certificate | Medium | Public distribution may trigger SmartScreen warnings; requires real code-signing certificate |
| `mpv/` directory not tracked in git | Low | Must be present at build time; installer bundles `mpv\` directory |
| Thai language installer requires `thai.nlf` in NSIS Contrib | Low | Installer falls back to English if `thai.nlf` not installed |

## 18. Rollback / Recovery Instructions

- **Code rollback:** `git revert <commit>` or `git reset --hard <previous-SHA>` on `main`
- **Installer rollback:** Previous installer versions remain available in GitHub Releases
- **Config rollback:** `config.toml.bak` is created by auto-discover before overwriting `config.toml`
- **Uninstall:** NSIS uninstaller removes all files, shortcuts, and registry entries

## 19. Next Actions

| Action | Owner | Status |
|--------|-------|--------|
| Obtain real code-signing certificate (OV/EV) for public distribution | Operator | Pending |
| Test on clean Windows VM without Camfrog pre-installed | Tester | Pending |
| Verify auto-discover works with different Camfrog versions | Tester | Pending |
| Document end-user installation steps in `docs/windows-install.md` | Writer | Pending |
## 16. Conclusion

Camfrog AutoDJ v0.2.6 is production-ready as a reusable GitHub template with a fully functional Camfrog AutoDJ music bot. All critical issues have been resolved, all tests pass, all CI checks pass, and the repository is clean with a working tree in sync with `origin/main`.
