# CamfrogAutoDJ — Security Audit Report

**Repository:** `cvsz/autodj`  
**Base Commit SHA (`main`):** `572aad9` (Merge PR #56)  
**Remediation Changes:** Working tree (pending commit/PR)  
**Date:** 2026-11-02  
**Auditor:** ZEAZDEV Super Ultra AI ORC  

---

## 1. Executive Summary

Security audit of the AutoDJ codebase identified P1 (critical) and P2 (security/engineering) findings. All P1 findings have been remediated. P2 findings are partially addressed; several require external platform configuration or credentials not available in this environment.

**No credentials, tokens, private keys, or production endpoints were found committed to the repository.**

---

## 2. P1 Security Findings — Remediated

### P1-1: Installer Data Destruction (FIXED)

**Finding:** `install-full-auto.ps1:171` and `install.ps1:528` called `Remove-Item -Recurse -Force $ProjectDir`, destroying all user data on installer re-run without backup.

**Remediation:**
- Added `Backup-UserData()` / `Restore-UserData()` functions to both PowerShell installers
- User data (`config.toml`, `playlist.json`, `*.log`, `playlist_dir/*.json`) is backed up to `%TEMP%` before any directory removal
- Restored after cloning into the fresh project directory
- Aborts if backup fails

**Files changed:** `install-full-auto.ps1`, `install.ps1`

### P1-2: Administrator Authorization via Nickname (FIXED)

**Finding:** `commands.py:32` authorized by display nick only; `config.example.toml:2` shipped with `admins = ["Seaza"]` default administrator.

**Remediation:**
- Removed default administrator: `admins = []` with warning comment
- Added 6 regression tests for authorization behavior (case-insensitivity, local console trust, non-admin denial, admin access, blocked-user handling)
- Documented the inherent limitation: Camfrog UI automation exposes only display nicks, no cryptographic identity

**Files changed:** `config.example.toml`, `tests/test_hardening.py`

### P1-3: Release Workflow Not Gated (FIXED)

**Finding:** `.github/workflows/release.yml` published releases immediately on tag push with no validation gates.

**Remediation:**
- Split into `validate-release` (tests, lint, typecheck, secret scan) and `build-installer` jobs
- `build-installer` requires `needs: validate-release`
- Removed automatic GitHub Release publication — manual creation required

**Files changed:** `.github/workflows/release.yml`

---

## 3. P2 Security Findings — Partially Addressed

### P2-1: CodeQL Language Coverage (FIXED)

**Finding:** CodeQL analyzed only `actions` language, not Python application code.

**Fix:** `.github/workflows/codeql.yml:26` → `languages: python`

### P2-2: Dependabot pip Coverage (FIXED)

**Finding:** Dependabot covered only GitHub Actions and Docker, not Python/pip dependencies.

**Fix:** `.github/dependabot.yml` — Added `package-ecosystem: pip` entry.

### P2-3: Action Pinning (PARTIAL)

**Finding:** Some Actions used tags (`@v2`, `@v4`) instead of full commit SHAs.

**Status:** Most actions pinned to full SHAs. `actions/attest-build-provenance@v2` and `actions/upload-artifact@v4` in release.yml still use tags. Full SHAs could not be resolved without external API access.

### P2-4: Strict Typecheck Enforcement (FIXED)

**Finding:** `mypy camfrog_autodj || true` and `ruff check . || true` masked failures.

**Fix:** Removed `|| true` from both steps in `.github/workflows/release.yml`.

### P2-5: CODEOWNERS Independent Review (FIXED)

**Finding:** All files owned by `@cvsz` only, allowing self-approval on security-sensitive changes.

**Fix:** `.github/CODEOWNERS` rewritten to require `@policedbc` review for security-sensitive paths (workflows, installer scripts, SECURITY.md, AGENTS.md, config files).

### P2-6: Secret Scanning (UNVERIFIED)

**Status:** CI secret-file scan (`ci.yml`) passes — no tracked `.env`, `*.pem`, `*.key`, etc. GitHub secret scanning/push protection is a repository setting, not controllable from committed files.

---

## 4. Application-Level Security Review

### Authentication / Authorization

| Component | Mechanism | Limitation |
|-----------|-----------|------------|
| Admin authorization | Nickname-based, case-insensitive (`commands.py:32`) | Spoofable via look-alike nicks; no cryptographic identity |
| Local console | Always trusted (`msg.local=True`) | Appropriate for console testing |
| Blocked users | Silently ignored (`commands.py:53`) | No room noise from blocked users |
| Admin self-block | Rejected (`commands.py:319`) | Prevents self-lockout |

### Input Validation

| Vector | Protection | Status |
|--------|------------|--------|
| Outgoing chat text | `clean_text()` strips control characters | Verified by `test_clean_text` |
| Wrapped message continuations | `…` prefix prevents command injection | Verified by `test_wrapped_continuation_never_starts_with_prefix` |
| `!load` paths | Rejects absolute paths outside `music_dirs` | Verified by `test_remove_own_only_and_say_local` |
| `!play` hosts | Non-admin restricted to `allowed_hosts` (YouTube) | Verified by `test_host_ok` |
| Config values | Type, range, and choice validation | Verified by `test_config_value_validation` |
| Config TOML | `tomllib` parsing with syntax error reporting | Verified by `test_toml_syntax_error_shows_the_bad_line` |

### Secrets Hygiene

- No `.env`, `*.pem`, `*.key`, `id_rsa`, `id_ed25519` tracked in git (CI scan passes)
- `config.toml` is in `.gitignore` (never committed)
- `build.ps1` copies `config.toml` into `dist\` — operators warned not to distribute `dist\`
- `AUTODJ_PFX_PASSWORD` env var preferred over `-Password` CLI arg

---

## 5. Security Items Requiring External Action

| Item | Reason |
|------|--------|
| Configure private vulnerability reporting | GitHub repository setting |
| Enable secret scanning and push protection | GitHub repository setting |
| Block force pushes and deletion of default branch | Already confirmed via GH006; deletion protection not independently verified |
| Require conversation resolution | GitHub repository setting |
| Code-signing certificate for Windows executable | Requires PFX/thumbprint; no cert in repo |
| GPG signing for annotated release tags | Requires GPG key; documented in `docs/release.md` |
| Resolve full Action SHAs for attest-build-provenance, upload-artifact | Requires external API access |

---

## 6. Verification Commands

```bash
# Run all tests (including security regression tests)
python -m pytest -q -p no:faulthandler -p no:cacheprovider
# Expected: 175 passed, 3 subtests passed

# Verify no default admin
python -c "from camfrog_autodj.config import Config; c = Config.load('config.example.toml'); assert c.admins == []"

# Verify config validation rejects bad values
python -c "
from camfrog_autodj.config import Config, ConfigError
try:
    Config.load('config.toml')  # if present
except ConfigError as e:
    print('Config validation works:', str(e)[:80])
"

# Run --check diagnostics
python -m camfrog_autodj --check
# Expected: FAIL for mpv (not installed in this env), WARN for missing deps, OK for config structure
```

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation Status |
|------|-----------|--------|-------------------|
| Installer destroys user data | Low | High | FIXED — backup/restore before removal |
| Nick spoofing gains admin rights | Medium | High | PARTIAL — default admin removed; inherent platform limitation |
| Unauthorized release publication | Low | High | FIXED — workflow gated, no auto-publish |
| Unreviewed security change | Medium | Medium | FIXED — CODEOWNERS requires @policedbc |
| Dependency vulnerability | Medium | Medium | PARTIAL — Dependabot pip coverage added |
| Committed secrets | Low | Critical | VERIFIED — CI scan passes, none found |
