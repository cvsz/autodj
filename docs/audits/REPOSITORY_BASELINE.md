# Repository Baseline — AutoDJ (CamfrogAutoDJ)

**Generated:** 2026-11-06  
**Branch:** `feat/autodj-enhancements-and-fixes`  
**HEAD SHA:** `79372556e26ab4c24f57f8b7b3eba8fe47dc4729`  
**Default branch:** `main` (up to date with `origin/main`)  
**Remote:** `git@github.com:cvsz/zcamfrog-autodj.git` (origin)  
**Application version:** `0.2.6` (`camfrog_autodj/__init__.py`)

## Working-tree state

| Item | State |
|------|-------|
| Uncommitted changes | None (clean) |
| Untracked files | `ausi-master-prompt.md`, `docs/recordings/`, `test_output.txt`, `test_script.ps1` |
| Commit on current branch | `7937255` fix: settings popup not working (2 files, +13/-0) |
| Previous commit | `8b11f2b` feat: autodj enhancements and fixes (13 files, +224/-33) |

## Branch inventory

Local branches:
- `feat/autodj-enhancements-and-fixes` (current, from `main`)
- `main`
- `chore/sync-release-0.2.5-and-quality`
- `docs/sync-all-documentation`
- `fix/autodj-executable-paths-release-gates`
- `fix/config-migration`
- `fix/config-migration-v2`
- `fix/installer-nsi-*` (multiple installer fix branches)
- `fix/load-folder-crash`
- `fix/player-countdown-time`
- `fix/playlist-not-play`
- `fix/production-qualification`
- `fix/production-runtime-*`
- `fix/security-remediation-p1-p2`
- `fix/test-and-ci-remediation`
- `fix/yt-dlp-ca-bundle`
- `qual/production-acceptance`
- `qual/windows-qualification-*`
- `style/ruff-format-12-files`
- `style/remove-unused-noqa-main`

## Source inventory

### Application source (`camfrog_autodj/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Version (`0.2.6`) |
| `__main__.py` | CLI entry point: `--check`, `--discover`, `--windows`, `--dump`, `--say`, `--gui`, `--console` |
| `adapters/__init__.py` | `NullAdapter`, `build_adapter()` factory |
| `adapters/base.py` | `ChatMessage` dataclass, `ChatAdapter` ABC, `parse_line()`, `diff_lines()` |
| `adapters/console.py` | stdin/stdout chat adapter (testing) |
| `adapters/logtail.py` | Read-only chat log file tailer |
| `adapters/uia.py` | Windows UI Automation adapter (pywinauto), background/foreground send |
| `clipkeys.py` | Cross-platform clipboard key handling |
| `commands.py` | `Router`, `@command` decorator, all `!` command implementations |
| `config.py` | `Config` dataclass, TOML loading + validation, `ConfigError` |
| `discover.py` | Auto-discovery of Camfrog window + chat controls |
| `doctor.py` | `--check` diagnostics |
| `engine.py` | `Engine`: chat loop, player loop, command router, autoplay pool, auto-reply |
| `gui.py` | Tk desktop window (studio UI), settings dialog, queue/history/chat |
| `launcher.py` | Camfrog auto-launch (`ensure_room`) |
| `library.py` | yt-dlp integration, local file scanning, `LocalIndex` |
| `messages.py` | All user-facing strings (en + th) |
| `migrate.py` | Config migration |
| `models.py` | `Track`, `UserError`, `YtdlpMissing`, `fmt_time()` |
| `paths.py` | Executable path resolution |
| `player.py` | `MpvPlayer`: one mpv process per track, IPC, fade in/out |
| `playlist.py` | `PlaylistStore`: persistent `playlist.json` |
| `playqueue.py` | `PlayQueue`: requests-first + autoplay pool, shuffle/repeat |
| `textutil.py` | `clean_text()`, `norm()` |
| `tts.py` | pyttsx3 TTS wrapper |
| `visuals.py` | GUI decorative visuals (aurora, equaliser, confetti) |
| `webchat.py` | Camfrog embedded web-pane chat parsing |
| `windows.py` | Window enumeration/resolution |
| `winmsg.py` | Windows message posting for background chat sending |

### Tests (`tests/`)

20 test files covering: core queue/commands, background clip, bootstrap, discover, executable paths, GUI i18n/logic, hardening (audit regressions), installer data safety, migration, play flow, playlist resolver, production remediation, pytest compat, v0.30 fixes, version/release, webchat dump, Windows build script, Windows qualification scripts.

### Configuration

| File | Status |
|------|--------|
| `config.toml` | Active config (mpv_timeout=0, auto-reply enabled=false, lang=th) |
| `config.example.toml` | Example template (mpv_timeout=30, admins=[], lang=th) |
| `config.default.toml` | Defaults (mpv_timeout=30, volume=70, lang=th) |

### Packaging & distribution

- `AutoDJ.spec` — PyInstaller spec
- `build.ps1` — PowerShell build/sign script
- `installer.nsi` — NSIS installer (per-user, `%APPDATA%\CamfrogAutoDJ`)
- `install.ps1` / `install.bat` — Automated Windows 11 installer
- `Camfrog-AutoDJ-Setup-0.2.6.exe` — Built installer (119 MB)
- `pyproject.toml`, `Dockerfile`, `Makefile`

### Documentation

| Document | Status |
|----------|--------|
| `README.md` | Current |
| `AGENTS.md` | Repository agent contract |
| `AUDIT.md` | v0.1.0→0.2.0 audit findings (F1–F15, O1–O9) |
| `ARCHITECTURE.md` (docs/) | Architecture overview |
| `CHANGELOG.md` | Changelog (Unreleased + 0.2.6) |
| `CONTRIBUTING.md` | Contribution guide |
| `GOVERNANCE.md` | Governance model |
| `ROADMAP.md` | Roadmap |
| `SECURITY.md` | Security policy |
| `ZEAZ-INTRODUCTION.md` | ZEAZ execution framework |

### CI (`.github/workflows/`)

`ci.yml`, `tests.yml`, `codeql.yml`, `dependency-review.yml`, `release.yml`

## Known audit findings from AUDIT.md (v0.1.0 → 0.2.0, all marked Fixed)

| ID | Severity | Finding |
|----|----------|---------|
| F1 | High | Bot executes its own `!help` reply as a command |
| F2 | High | Failing track retried with no delay, floods room |
| F3 | High | `AutoDJ.exe` built without `yt_dlp` module |
| F4 | Medium | Invalid `config.toml` → raw traceback |
| F5 | Medium | No config validation |
| F6 | Medium | `!remove`/GUI Remove acts on stale queue position |
| F7 | Medium | `max_requests_per_user` bypassed by overlapping requests |
| F8 | Low-Med | Auto-discovery writes invalid TOML / non-atomically |
| F9 | Low | mpv `--really-quiet` makes failures undiagnosable |
| F10 | Low | `pause`/`resume` flips state even when mpv rejects |
| F11 | Low | GUI poll loop dies on one exception; unbounded chat widget |
| F12 | Low | Control chars in outgoing text; duplicate autoplay entries; non-interruptible send sleep |
| F13 | Info | `AutoDJ.spec` stale vs `build.ps1`; UPX antivirus false positives |
| F14 | High | `uia.py` `_appeared()`: `UnboundLocalError` on every background send |
| F15 | High | `winmsg.py`: duplicate function definitions shadow first |

## Open items from AUDIT.md (not changed)

- **O1** Admin = display nick only (no cryptographic identity)
- **O2** CPU: UIA reader walks ~600 controls 2x/sec
- **O3** Camfrog UI automation is version-fragile
- **O4** One-file exe unpacks on every start (AV dislike)
- **O5** yt-dlp ages quickly
- **O6** TTS untested
- **O7** Secrets hygiene: `build.ps1` copies live `config.toml` into `dist\`
- **O8** No persisted state (queue, volume, shuffle reset on restart)
- **O9** mpv control pipe name is predictable

## Verification evidence

- `python -m ruff check camfrog_autodj/` — **passed** (0 errors)
- `python -m pytest tests/ -q` — **288 passed, 3 subtests passed**

## Currently implemented features on this branch (from prior work session)

1. `mpv_timeout` default = `0.0` in `config.py` and `config.toml`
2. `MpvPlayer.seek()` + `Engine.seek()` (mpv IPC absolute seek)
3. `GlowBar` click-to-seek + `App._on_seek()` in `gui.py`
4. Double-click queue item → move to front (`PlayQueue.add_request(t, position=0)`)
5. `ChatMessage.is_im` field in `adapters/base.py`
6. IM command handling (no prefix required) in `commands.py`
7. `clearhistory` admin command in `commands.py` + `history_cleared` strings (en/th)
8. Auto-reply config (`auto_reply_enabled`, `auto_reply_interval`, `auto_reply_file`)
9. `_auto_reply_loop` + `_load_auto_reply_messages` in `engine.py`; `ads-list.json` created
10. Auto-reply settings UI in `gui.py` `open_settings()` + `save_settings()`
11. `library.py`: `local_track()` catches all exceptions; `scan_folder()` skips bad files individually
12. `console.py`: `im nick: text` format for IM messages
13. `logtail.py` / `uia.py`: IM detection via `[IM]` tag or `IM ` prefix
14. Message keys for auto-reply settings in `messages.py` (en/th)
