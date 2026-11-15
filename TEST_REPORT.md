# Test Report — CamfrogAutoDJ v0.3.0

**Date:** 2026-11-16  
**Branch:** main (HEAD: fecc053)  
**Platform:** Windows 11 (Python 3.14.8)  
**Repository:** https://github.com/cvsz/autodj

---

## Test Summary

| Metric | Result |
|--------|--------|
| Total tests | 524 passed |
| Failed | 0 |
| Skipped | 3 |
| Subtests passed | 3 |
| Warnings | 1 (pywinauto STA threading, not our code) |
| Duration | ~28 seconds |

---

## Test Execution Command

```bash
python -m pytest -q -p no:faulthandler -p no:cacheprovider
```

**Output:** `524 passed, 3 skipped, 1 warning, 3 subtests passed in 27.84s`

---

## Test Files (48 test modules)

| Test Module | Description |
|-------------|-------------|
| `test_admin_commands.py` | Admin command handling and authorization |
| `test_admin_path_traversal.py` | Path traversal prevention for admin commands |
| `test_autodj_enhancements.py` | AutoDJ enhancement features (circuit breakers, rate limiting, health checks) |
| `test_background_clip.py` | Background clipboard operations |
| `test_bootstrap.py` | Bootstrap and startup behavior |
| `test_build_cross_platform.py` | Cross-platform build verification |
| `test_camfrog_font.py` | Camfrog font detection and parsing |
| `test_chat_loop_exceptions.py` | Chat loop exception handling |
| `test_concurrency.py` | Concurrency and thread safety |
| `test_config_hot_reload.py` | Configuration hot reload with watchdog |
| `test_core.py` | Core engine functionality |
| `test_discover.py` | Auto-discovery of Camfrog window/controls |
| `test_discover_regex.py` | Discovery regex patterns |
| `test_doctor_symlinks.py` | Doctor symlink safety |
| `test_doctor_uia_match.py` | Doctor UIA adapter matching |
| `test_empty_prefix.py` | Empty command prefix handling |
| `test_executable_paths.py` | Executable path resolution |
| `test_gui_i18n.py` | GUI internationalization (EN/TH) |
| `test_gui_logic.py` | GUI logic against fake Tk |
| `test_hardening.py` | Security hardening tests |
| `test_installer_data_safety.py` | Installer data safety (user data preservation) |
| `test_installer_version_substitution.py` | Installer version substitution |
| `test_json_logging.py` | JSON structured logging |
| `test_library_scan_safety.py` | Library scan safety (symlinks, limits, permissions) |
| `test_linux_builder_cli.py` | Linux builder CLI |
| `test_makefile_build_dispatch.py` | Makefile build dispatch |
| `test_migration.py` | Configuration migration (placeholder detection) |
| `test_nonblocking_backoff.py` | Non-blocking backoff patterns |
| `test_participant_count.py` | Participant count tracking |
| `test_pause_ipc_failure.py` | Pause IPC failure handling |
| `test_play_flow.py` | Play queue and track flow |
| `test_player_cache.py` | MPV player position caching |
| `test_playlist_resolver.py` | Playlist source validation |
| `test_pop_next_track.py` | Next track popping logic |
| `test_production_remediation.py` | Production remediation fixes |
| `test_pytest_compat.py` | Pytest compatibility |
| `test_targeted_coverage.py` | Targeted coverage for migrate/detect_placeholders |
| `test_tts_ducking.py` | TTS volume ducking |
| `test_v030_fixes.py` | v0.3.0 bug fixes |
| `test_version_and_release.py` | Version and release consistency |
| `test_version_consistency.py` | Version consistency across artifacts |
| `test_webchat_dump.py` | Web chat dump parsing |
| `test_webhook_server.py` | Webhook server tests |
| `test_windows_build_script.py` | Windows build script validation |
| `test_windows_qualification_scripts.py` | Windows qualification scripts |

---

## Quality Gates

| Gate | Command | Result |
|------|---------|--------|
| Lint (ruff) | `python -m ruff check camfrog_autodj tests tools` | All checks passed |
| Format (ruff) | `python -m ruff format --check camfrog_autodj tests tools` | 98 files already formatted |
| Type check (mypy) | `python -m mypy camfrog_autodj` | Success: no issues in 44 source files |
| Compile (compileall) | `python -m compileall -q camfrog_autodj tests tools` | exit 0 (no syntax errors) |
| Shell scripts (shellcheck) | `shellcheck scripts/*.sh tools/*.sh` | Clean |

---

## Test Coverage Notes

- High coverage (80%+): `__init__.py`, `exceptions.py`, `models.py`, `textutil.py`, `messages.py`, `visuals.py`, `config.py`, `playqueue.py`, `logging_json.py`, `clipkeys.py`, `webhook/models.py`, `webhook/__init__.py`
- Moderate coverage (60-80%): `playlist.py`, `migrate.py`, `config_watcher.py`, `renderer.py`, `gui.py`, `camfrog_font.py`, `paths.py`, `webhook/auth.py`, `discover.py`, `doctor.py`, `tts.py`, `library.py`, `player.py`, `webchat.py`, `launcher.py`, `commands.py`, `engine.py`, `webhook/server.py`
- Low coverage (<60%): `adapters/uia.py` (Windows UIA only), `adapters/console.py` (integration), `adapters/logtail.py` (integration), `adapters/__init__.py` (dispatcher), `windows.py` (Windows only), `winmsg.py` (Windows only), `plugins/manager.py` (plugin system), `plugins/base.py` (base classes), `plugins/builtin/*.py` (builtin plugins)

Low coverage in platform-specific adapters and builtin plugins is expected — these are integration points tested manually on Windows.

---

## Known Skips

3 tests are skipped (platform-specific or integration-heavy). No tests are disabled to obtain green CI.

---

## Regressions

No unexplained test regressions. All tests that passed in the previous baseline continue to pass.
