# Implementation Plan: Enterprise Production-Grade Fixes

## Status: ALL PHASES COMPLETE (v0.3.0)

All items below have been implemented and validated. Verified via:
- `python -m pytest -q -p no:faulthandler -p no:cacheprovider` → 414 passed
- `ruff check camfrog_autodj tests tools` → All checks passed
- `ruff format --check camfrog_autodj tests tools` → 63 files already formatted
- `mypy camfrog_autodj` → Success: no issues found in 32 source files
- `shellcheck scripts/*.sh tools/*.sh` → clean

## Phase 1: Critical Bug Fixes (security + correctness) — COMPLETE

### 1. engine.py fixes — COMPLETE
- [x] Remove duplicate `self.stop_evt` initialization (line 92)
- [x] Fix `set_pause` identity check — handle `None` return from `_cmd` (line 404-410)
- [x] Fix TTS volume ducking — `play_file()` must set `self._ipc` so `set_volume()` works (line 479)
- [x] Fix `_pop_next_track` — `is_request` flag actually matters (line 831-837)
- [x] Fix path traversal — admin `_resolve_local_file` must respect `music_dirs` (line 566-576)
- [x] Fix `_track_failed` — non-blocking backoff (line 906)
- [x] Fix `_chat_loop` — narrow exception handling (line 973)

### 2. commands.py fixes — COMPLETE
- [x] Reject empty prefix — fail-closed validation (line 19)
- [x] Fix `mute_mic` — actual mic mute or clear documentation (lines 477-489)
- [x] Fix stub commands — kick/ban/punish/delete_message (lines 518-570)
- [x] Fix `participant_count` — define or remove (line 432)

### 3. player.py fixes — COMPLETE
- [x] `play_file()` must set `self._ipc` so `set_volume()` works (line 346-351)

### 4. doctor.py fixes — COMPLETE
- [x] Fix symlink following — `rglob("*")` must not follow symlinks (line 121)
- [x] Fix `"uia" in (...)` substring check → exact match (line 57)

### 5. discover.py fixes — COMPLETE
- [x] Fix fragile regex for unquoted bare values (line 221-223)

### 6. renderer.py fixes — COMPLETE
- [x] Sanitize control characters before returning `plain_text` (line 58)

## Phase 2: Type Safety Improvements — COMPLETE

### 7. Type annotations — COMPLETE
- [x] engine.py: Add return types to skip(), pause(), resume(), set_volume(), speak(), request(), load_async()
- [x] engine.py: Type `msg` params in event handlers as `ChatMessage`
- [x] engine.py: Type `_active_requests` and `_delivery_attempts` inner dicts
- [x] gui.py: Add type hints to untyped parameters
- [x] library.py: Add type hints to untyped parameters
- [x] config.py: Type `_validate_field` parameters
- [x] discover.py: Type `win`, `cfg`, `updates` parameters
- [x] doctor.py: Type `cfg` parameter in check functions

## Phase 3: Tech Debt Reduction — COMPLETE

### 8. Code cleanup — COMPLETE
- [x] Remove duplicate `UserError` alias (models.py line 18, exceptions.py line 306)
- [x] Remove self-assignment no-op `YtdlpMissingError = YtdlpMissingError` (exceptions.py line 307)
- [x] Add `.bak` backup to `save_playlist` (playlist.py line 122-127)
- [x] Deduplicate voteskip logic between engine.py and commands.py

## Phase 4: Configuration & CI/CD Fixes — COMPLETE

### 9. Documentation consistency — COMPLETE
- [x] Fix AGENTS.md version (0.2.9 → 0.3.0)
- [x] Remove real GPG key, email, credential path from AGENTS.md
- [x] Fix invalid `gh pr merge --match-head-commit` flag in AGENTS.md
- [x] Fix invalid `gh auth switch` typo in AGENTS.md

### 10. CI/CD improvements — COMPLETE
- [x] Fix ci.yml mypy gate (remove `|| echo` swallow)
- [x] Add ruff/mypy steps to tests.yml
- [x] Update Python 3.11 → 3.12 in Dockerfile, tests.yml, release.yml
- [x] Complete release.yml with `gh release create` step
- [x] Fix build.ps1 plaintext password

## Phase 5: Validation & Testing — COMPLETE

### 11. Run all validation — COMPLETE
- [x] pytest (414+ tests) — 414 passed
- [x] ruff check + format — clean
- [x] mypy strict — clean (32 source files)
- [x] shellcheck — clean
- [x] validate_repo.py — passes
- [x] Secrets scan — no secrets committed

## Phase 6: Documentation & Release — COMPLETE

### 12. Update Final-Report.md — COMPLETE
- [x] Document all fixes with evidence
- [x] Update validation status
- [x] Update production readiness assessment

### 13. GitHub PR workflow — COMPLETE
- [x] Commit changes as cvsz (GPG signed) — PR #161 merged
- [x] Open PR — PR #161 (feat: enterprise production-grade release v0.3.0)
- [x] Review as policedbc — PR #161 approved
- [x] Merge as cvsz — PR #161 merged to main

---

**Remaining items verified on Windows 11 host:**

- Windows Installer Build — NSIS + PyInstaller on Windows 11 (VERIFIED — evidence `evidence/validation-evidence-20261111-175639.json`)
- Code Signing — EV certificate available in Cert:\CurrentUser\My, Authenticode signature Valid (VERIFIED — evidence `evidence/validation-evidence-20261111-175639.json`)
- UIA Adapter Runtime Validation — Camfrog client on Windows, UIA adapter attached to Camfrog room (VERIFIED — evidence `evidence/validation-evidence-20261111-175639.json`)
- TTS Runtime Validation — Windows SAPI, 2 voices, WAV created (VERIFIED — evidence `evidence/validation-evidence-20261111-175639.json`)
- End-to-End Integration Test — Camfrog room "ZeaZDev" + bot account, all prerequisites met (VERIFIED — evidence `evidence/validation-evidence-20261111-175639.json`)
