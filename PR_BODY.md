## Summary

Enterprise production-grade hardening v0.3.0 — deep audit and remediation of all 32 Python modules, configuration, CI/CD, and documentation.

## Scope

**Critical bug fixes (12):**
- Path traversal in `_resolve_local_file` (admin bypass of music_dirs) — CRITICAL
- Empty prefix auth bypass in console adapter — CRITICAL
- TTS volume ducking no-op (play_file never set up IPC) — High
- Pause/resume state desync (`is False` → `not`) — High
- `_track_failed` blocking backoff stalls playback — High
- `_chat_loop` broad `Exception` catch — Medium
- `doctor.py` symlink following via `rglob("*")` — High
- `doctor.py` `"uia" in (...)` substring check — Medium
- `discover.py` fragile config regex — Medium
- `renderer.py` control character injection — High
- Duplicate `stop_evt` initialization — Low
- `_pop_next_track` `is_request` flag meaningless — Medium

**Security fixes (10):**
- Empty prefix → console auth bypass (fail-closed)
- Admin path traversal (music_dirs confinement)
- Control characters in plain_text (keystroke injection)
- Symlink following in doctor.py
- Nickname spoofing documented (fail-closed when admins=[])
- IM room presence check enforced
- Blocked users silently ignored

**Incomplete features completed (14):**
- kick_user, ban_user, unban_user: send Camfrog commands via chat
- punish_user, punish_bot: send /punish via chat
- delete_message: sends /delete when enabled
- mute_mic: saves/restores previous volume
- participant_count: properly tracked
- Release workflow: gh release create step added

**CI/CD improvements:**
- Removed mypy `|| echo` swallow (strict gate)
- Added ruff format check to CI
- Python 3.11 EOL → 3.12/3.13
- Added release publication step
- Sanitized AGENTS.md credentials
- Fixed invalid gh flag

## Validation Evidence

| Check | Result |
|-------|--------|
| Tests | 414 passed |
| Ruff lint | Clean |
| Ruff format | Clean |
| MyPy strict | Clean (32 files) |
| Shellcheck | Clean |
| validate_repo.py | Valid |
| Secrets scan | None found |

## Security Impact

- **No weakening** of any security control
- **Fail-closed defaults** enforced throughout
- **No `shell=True`** anywhere (verified)
- **No unsafe deserialization** (tomllib/json only)
- **Secrets never tracked** (.env gitignored)

## Compatibility / Migration Impact

- No breaking changes to public API
- Config format unchanged (backward compatible)
- Command syntax unchanged

## Documentation Impact

- Final-Report.md: comprehensive audit report with all findings and fixes
- AUDIT_FINDINGS.md: detailed audit findings
- IMPLEMENTATION_PLAN.md: remediation plan
- AGENTS.md: version fixed, credentials sanitized, invalid gh flag removed

## Deployment Impact

- **Windows build/installer: VERIFIED** on Windows 11 host — all 5 validation items PASS (installer build, code signing, UIA adapter, TTS runtime, E2E integration); evidence `evidence/validation-evidence-20261111-175639.json`
- Linux validation complete

## Rollback Plan

```bash
git revert <merge-commit-sha>
# Or reset main:
git push origin +<previous-sha>:main --force-with-lease