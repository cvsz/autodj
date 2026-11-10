# Implementation Plan: Enterprise Production-Grade Fixes

## Phase 1: Critical Bug Fixes (security + correctness)

### 1. engine.py fixes
- [ ] Remove duplicate `self.stop_evt` initialization (line 92)
- [ ] Fix `set_pause` identity check — handle `None` return from `_cmd` (line 404-410)
- [ ] Fix TTS volume ducking — `play_file()` must set `self._ipc` so `set_volume()` works (line 479)
- [ ] Fix `_pop_next_track` — `is_request` flag actually matters (line 831-837)
- [ ] Fix path traversal — admin `_resolve_local_file` must respect `music_dirs` (line 566-576)
- [ ] Fix `_track_failed` — non-blocking backoff (line 906)
- [ ] Fix `_chat_loop` — narrow exception handling (line 973)

### 2. commands.py fixes
- [ ] Reject empty prefix — fail-closed validation (line 19)
- [ ] Fix `mute_mic` — actual mic mute or clear documentation (lines 477-489)
- [ ] Fix stub commands — kick/ban/punish/delete_message (lines 518-570)
- [ ] Fix `participant_count` — define or remove (line 432)

### 3. player.py fixes
- [ ] `play_file()` must set `self._ipc` so `set_volume()` works (line 346-351)

### 4. doctor.py fixes
- [ ] Fix symlink following — `rglob("*")` must not follow symlinks (line 121)
- [ ] Fix `"uia" in (...)` substring check → exact match (line 57)

### 5. discover.py fixes
- [ ] Fix fragile regex for unquoted bare values (line 221-223)

### 6. renderer.py fixes
- [ ] Sanitize control characters before returning `plain_text` (line 58)

## Phase 2: Type Safety Improvements

### 7. Type annotations
- [ ] engine.py: Add return types to skip(), pause(), resume(), set_volume(), speak(), request(), load_async()
- [ ] engine.py: Type `msg` params in event handlers as `ChatMessage`
- [ ] engine.py: Type `_active_requests` and `_delivery_attempts` inner dicts
- [ ] gui.py: Add type hints to untyped parameters
- [ ] library.py: Add type hints to untyped parameters
- [ ] config.py: Type `_validate_field` parameters
- [ ] discover.py: Type `win`, `cfg`, `updates` parameters
- [ ] doctor.py: Type `cfg` parameter in check functions

## Phase 3: Tech Debt Reduction

### 8. Code cleanup
- [ ] Remove duplicate `UserError` alias (models.py line 18, exceptions.py line 306)
- [ ] Remove self-assignment no-op `YtdlpMissingError = YtdlpMissingError` (exceptions.py line 307)
- [ ] Add `.bak` backup to `save_playlist` (playlist.py line 122-127)
- [ ] Deduplicate voteskip logic between engine.py and commands.py

## Phase 4: Configuration & CI/CD Fixes

### 9. Documentation consistency
- [ ] Fix AGENTS.md version (0.2.9 → 0.3.0)
- [ ] Remove real GPG key, email, credential path from AGENTS.md
- [ ] Fix invalid `gh pr merge --match-head-commit` flag in AGENTS.md
- [ ] Fix invalid `gh auth switch` typo in AGENTS.md

### 10. CI/CD improvements
- [ ] Fix ci.yml mypy gate (remove `|| echo` swallow)
- [ ] Add ruff/mypy steps to tests.yml
- [ ] Update Python 3.11 → 3.12 in Dockerfile, tests.yml, release.yml
- [ ] Complete release.yml with `gh release create` step
- [ ] Fix build.ps1 plaintext password

## Phase 5: Validation & Testing

### 11. Run all validation
- [ ] pytest (414+ tests)
- [ ] ruff check + format
- [ ] mypy strict
- [ ] shellcheck
- [ ] validate_repo.py
- [ ] Secrets scan

## Phase 6: Documentation & Release

### 12. Update Final-Report.md
- [ ] Document all fixes with evidence
- [ ] Update validation status
- [ ] Update production readiness assessment

### 13. GitHub PR workflow
- [ ] Commit changes as cvsz (GPG signed)
- [ ] Open PR
- [ ] Review as policedbc
- [ ] Merge as cvsz
