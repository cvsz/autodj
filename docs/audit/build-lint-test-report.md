# Build / Lint / Test Report — CamfrogAutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`  
**Platform:** Linux, Python 3.14.4  
**Audit date:** 2026-11-08

## Commands run and results

| Command | Exit code | Result |
|---------|-----------|--------|
| `python3 -m pytest -q -p no:cacheprovider` | 0 | **336 passed, 3 subtests passed** |
| `ruff check camfrog_autodj tests tools` | 0 | **All checks passed** |
| `ruff format --check camfrog_autodj tests tools` | 0 | **57 files already formatted** |
| `python3 -m compileall -q camfrog_autodj tests tools` | 0 | **Compiled cleanly** |
| `shellcheck scripts/*.sh tools/*.sh` | 0 (warnings) | Minor style warnings only (SC2181, SC2034) |

## Test detail

- Baseline before this audit: **325 passed**.
- Added: `tests/test_library_scan_safety.py` — **11 new regression tests** for library scan symlink/reparse-point safety.
- After this audit: **336 passed, 3 subtests passed**, in ~15.6s.
- No tests skipped, no failures.

## Ruff detail

`pyproject.toml` configures a focused rule set (`E, F, B, I, C, N, S`) with `line-length = 100`. The one fixable finding (unsorted import in the new test file) was fixed with `ruff check --fix` and re-verified: `ruff check` passes clean. No warnings were swallowed with `|| echo warning`. No `noqa` suppressions were added to hide genuine issues.

## ShellCheck detail

Ran against `scripts/*.sh` and `tools/*.sh`:
- `scripts/build_installer_linux.sh:77` SC2181 — check exit code directly, not via `$?`. (Style; script is Linux/WSL-only installer helper.)
- `scripts/deploy-workflow-all-repos.sh:19` SC2034 — `ACCOUNTS_FILE` appears unused. (Style.)
- `scripts/gh-switch.sh:49` SC2034 — `ORIG_URL` appears unused. (Style.)

None are defects; all are pre-existing style notes in multi-repo/tooling scripts outside the application core. No `bash -n` failures.

## Windows build (VERIFIED on Windows 11 host)

- `build.ps1`, PyInstaller, `installer.nsi`, `makensis` — **VERIFIED** on Windows 11 host — evidence `evidence/validation-evidence-20261111-175639.json` (5 passed, 0 failed, 0 skipped).
- `make build`/`make installer` require Windows PowerShell; verified via `scripts/build_installer.ps1 -Version 0.3.0 -Sign`.
- `test_windows_build_script.py` and `test_windows_qualification_scripts.py` are present and run as part of pytest (they parse/validate scripts where platform-appropriate).

## Docker

`Dockerfile` is present. Docker build was not part of this audit's executed commands (no container runtime target specified); the Makefile has no `docker` target.

## New regression test added

`tests/test_library_scan_safety.py` — 11 tests pinning `scan_folder`/`LocalIndex` symlink safety (Phase 3 critical regression tests: symlink cycles, reparse-point cycles, broken symlinks, unreadable directories, limits, Unicode).
