# Production Readiness — Camfrog AutoDJ

**Repository:** github.com/cvsz/autodj  
**Version:** 0.2.8 (`pyproject.toml`, `camfrog_autodj/__init__.py`)  
**Baseline SHA:** `fb5e99a`  
**Platform:** Linux audit host; Windows runtime/installer BLOCKED

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
| Windows build | PyInstaller + NSIS installer | BLOCKED | no Windows host |
| Installer tested | Windows install/uninstall | BLOCKED | no Windows host |
| Real Camfrog integration | authorized test environment | NOT IMPLEMENTED | mocks only; no live Camfrog |
| Real mpv/yt-dlp playback | authorized media | NOT IMPLEMENTED | no real media on host |

## Production readiness verdict

**NOT PRODUCTION-READY on this host**, and the verdict cannot be upgraded until:

1. GPG signing works (signed commits as cvsz, policedbc approval, cvsz merge).
2. Windows build + NSIS installer built and verified on Windows 11.
3. Installer tested (install/uninstall/upgrade/user-data preservation).
4. Real Camfrog integration validated in an authorized test environment (mocks alone do not prove integration).

Linux unit/test validation passes. All Windows-specific and live-integration claims are explicitly marked BLOCKED or NOT IMPLEMENTED — none are claimed as passing based on Linux-only checks.
