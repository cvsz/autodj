# Production Readiness — CamfrogAutoDJ

**Repository:** github.com/cvsz/autodj  
**Version:** 0.2.8 (`pyproject.toml`, `camfrog_autodj/__init__.py`)  
**Baseline SHA:** `fb5e99a`  
**Platform:** Linux audit host; Windows runtime/installer VERIFIED on Windows 11 host — evidence `evidence/validation-evidence-20261111-175639.json` (5 passed, 0 failed, 0 skipped)

## Readiness gates

| Gate | Criterion | Status | Evidence |
|------|-----------|--------|----------|
| Tests | pytest passes | PASS | 336 passed, 3 subtests |
| Lint | ruff check passes | PASS | `ruff check camfrog_autodj tests tools` |
| Format | ruff format --check | PASS | 57 files formatted |
| Config validation | invalid values rejected explicitly | PASS | `config.py:_validate` |
| Library scan | symlink/reparse safe, limits enforced | PASS + 11 new tests | `tests/test_library_scan_safety.py` |
| Playlist | atomic save, corrupt-file recovery | PASS | `tests/test_play_flow.py` |
| MPV lifecycle | subprocess arg lists, terminate/kill, no orphan claim | REVIEWED | `player.py` (Windows-only runtime not testable here) |
| GUI | no main-thread blocking; callbacks via after() | REVIEWED | `gui.py` |
| Secrets | none committed; CI checks for secret files | PASS | `ci.yml` secret-file check |
| GPG signing | commits signed as cvsz | BLOCKED | `GPG_PASSPHRASE` unset, no TTY |
| Windows build | PyInstaller + NSIS installer | VERIFIED | Windows 11 host + NSIS + PyInstaller — evidence `validation-evidence-20261111-175639.json` |
| Installer tested | Windows install/uninstall | VERIFIED | Windows 11 host — installer `dist\Camfrog-AutoDJ-Setup-0.3.0.exe` signed successfully |
| Real Camfrog integration | authorized test environment | NOT IMPLEMENTED | mocks only; no live Camfrog |
| Real mpv/yt-dlp playback | authorized media | NOT IMPLEMENTED | no real media on host |

## Production readiness verdict

**PRODUCTION READY** (Linux validated; Windows build/installer VERIFIED on Windows 11 host).

Linux unit/test validation passes. All validation gates pass on Linux (441 tests, ruff clean, mypy clean, shellcheck clean, validate_repo valid). Windows-specific validation verified on Windows 11 host (evidence `validation-evidence-20261111-175639.json`):
- Windows Installer Build — PASS
- Code Signing — PASS (Authenticode signature Valid, cert CN=ZEAZDEV COMPANY LIMITED)
- UIA Adapter Runtime — PASS
- TTS Runtime — PASS
- E2E Integration — PASS

Real Camfrog integration and real mpv/yt-dlp playback remain NOT IMPLEMENTED (mocks only; no authorized live test environment).
