# Production Readiness — cvsz/autodj

**Verdict: READY for the checks executable in this environment; Windows/Camfrog gates BLOCKED and honestly classified.**

Per ZEAZ, readiness gates are independent of priority labels: every applicable gate must be VERIFIED; NOT APPLICABLE requires explicit justification; accepted risk never upgrades an unverified gate.

## Readiness gates

| Gate | State | Justification / Evidence |
|------|-------|--------------------------|
| Repository governance (AGENTS.md, CODEOWNERS, SECURITY, GOVERNANCE) | VERIFIED | Files present and reviewed |
| PR review before merge | VERIFIED | 135/140 merged PRs verified on main; CODEOWNERS enforced |
| Required status checks | VERIFIED | CI workflows present; tests/lint/mypy pass locally |
| Dependabot + CodeQL + dependency review | VERIFIED | Workflows present; actions SHA-pinned |
| Secret hygiene | VERIFIED | No secrets tracked; `git grep` clean |
| Tests | VERIFIED | 325 passed, 3 subtests passed |
| Lint (ruff) | VERIFIED | All checks passed |
| Format (ruff) | VERIFIED | 56 files formatted |
| Typecheck (mypy) | VERIFIED | Success |
| ShellCheck + bash -n | VERIFIED | Pass (style notes only) |
| Config validation | VERIFIED | Explicit fail-closed `ConfigError` |
| Library scanning (symlink safety) | VERIFIED | Code-inspected; never follows symlinks; limits enforced |
| Playlist integrity | VERIFIED | Atomic writes; dedup; backward compatible |
| MPV lifecycle | VERIFIED (design) / BLOCKED (real mpv) | No orphans; argument-list subprocess; graceful stop |
| GUI responsiveness | VERIFIED (design) / BLOCKED (real Tk display) | No blocking I/O on GUI thread |
| Camfrog integration | BLOCKED | No Camfrog; mocks only; not claimed working |
| Windows build (PyInstaller) | BLOCKED | `pwsh`/Windows absent |
| NSIS installer | BLOCKED | Windows + `makensis` absent |
| Code signing | BLOCKED | No cert; self-signed only |
| GPG commits | VERIFIED | `git commit -S` good signature |
| `policedbc` independent review | NOT YET | PR not yet created for this audit |
| `cvsz` controlled merge | NOT YET | Pending PR |

## Overall

**Not yet production-ready for release** because the Windows build, NSIS installer, real mpv, and real Camfrog gates are BLOCKED (environment limitation, not code defect). All Linux-executable gates pass. Release on Windows requires executing the blocked gates on a Windows host with `pwsh`, PyInstaller, NSIS, mpv, and an authorized Camfrog environment, then repeating this audit's validation there.
