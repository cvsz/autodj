# Security Audit — CamfrogAutoDJ

**Repository:** cvsz/autodj  
**Branch:** `feat/autodj-enhancements-and-fixes`  
**HEAD SHA:** `2c2f6f2`  
**Application version:** `0.2.6`  
**Audit date:** 2026-11-06  
**Auditor:** AUSI Security Reviewer

## Executive Summary

The AutoDJ application has a sound security foundation: nickname-based admin authorization with explicit opt-in, silent block listing, outgoing text sanitisation, command prefix requirement for room messages, and path traversal protection for `!load`. The IM command feature adds a controlled path for private-message control (no prefix required but cooldown/rate limits still apply). No critical (P0) security defects were found. The primary security limitation is inherent to the platform: Camfrog UI Automation exposes only display nicks, so admin authorization cannot be cryptographically strong.

## Threat Model

| Threat | Mitigation | Residual Risk |
|--------|-----------|---------------|
| Nickname spoofing → admin escalation | `admins = []` by default; operator must add nick; case-insensitive match | **High** — anyone displaying the same nick gains admin rights |
| Command injection via wrapped text | Continuation lines prefixed with `…` | Low |
| Control character injection | `clean_text()` strips control characters | Low |
| Path traversal via `!load` | Absolute paths rejected outside `music_dirs` (admin-only) | Low |
| Command flooding | Per-user cooldown + sliding-window rate limit | Low |
| Room spam from failing tracks | Max 3 failure announcements, then log-only + backoff | Low |
| IM-based unauthorized control | Cooldown/rate limits still apply; blocked users ignored | Low |
| Config file secrets exposure | No credentials committed; `build.ps1` copies live `config.toml` to `dist\` | Medium (operator responsibility) |

## Detailed Findings

### P0 — Critical security defects

None found.

### P1 — Major security defects

None found.

### P2 — Security weaknesses

| ID | Severity | File | Finding | Impact | Recommendation |
|----|----------|------|---------|--------|----------------|
| S-01 | P2 | `camfrog_autodj/commands.py:31-32` | Admin authorization is nickname-based only (`msg.user.lower() in self.e.admins`). Camfrog UI Automation exposes display nicks, not cryptographic identities. | Anyone who can display the same nick (look-alike Unicode, nick freed by disconnect) gains admin rights. | Document clearly (already in AUDIT.md O1 and README caveats). Keep `admins` list short. Use unique nicks. |
| S-02 | P2 | `camfrog_autodj/build.ps1` | Copies live `config.toml` into `dist\` directory. | If `dist\` is shared, admin nicks and other settings are exposed. | Already documented in AUDIT.md O7 and README. Use `AUTODJ_PFX_PASSWORD` env var instead of `-Password`. |
| S-03 | P2 | `camfrog_autodj/player.py:90-94` | mpv IPC pipe name is predictable: `\\.\pipe\camfrog-autodj-{pid}-{n}`. | Any local process of the same user could send IPC commands to mpv (pause, seek, volume). | Low risk on a personal PC (already documented as O9 in AUDIT.md). |

### P3 — Optional security improvements

| ID | Severity | File | Finding | Recommendation |
|----|----------|------|---------|----------------|
| S-04 | P3 | `camfrog_autodj/adapters/uia.py` | UIA reader walks ~600 child controls twice a second (CPU). | Already documented as O2. `poll_interval` is the knob (default 0.5s). |
| S-05 | P3 | `camfrog_autodj/engine.py` | `_auto_reply_loop` sends messages even when adapter is `NullAdapter`. | Acceptable — `NullAdapter.send()` is a no-op, messages are silently dropped. |
| S-06 | P3 | `camfrog_autodj/commands.py` | IM commands bypass the prefix requirement but still apply cooldown/rate limits. | Intentional design. Cooldown/rate limits provide basic abuse protection. |

## Authentication / Authorization analysis

### Admin model

```
is_admin(msg) = msg.local OR msg.user.lower() in self.e.admins
```

- `local=True` (console/stdin): always trusted as admin
- Room messages: nickname must match a configured admin (case-insensitive)
- IM messages: same authorization check, no prefix required

**Limitation:** No cryptographic identity. Camfrog UI Automation only exposes display nicks. This is an inherent platform limitation, not an implementation defect.

### Block list

```
blocked: set of lowercase nicks whose commands are ignored silently
```

- Blocked users get no room reply (no noise)
- Admins cannot be blocked (`_block` checks `nick.lower() in e.admins`)
- Blocked users cannot block themselves or other admins

### Input validation

| Vector | Protection |
|--------|-----------|
| Outgoing text | `clean_text()` strips control chars, collapses whitespace |
| Wrapped continuations | Prefixed with `…` so they never look like commands |
| `!load` paths | Absolute paths must be within `music_dirs` (admin-only) |
| `!play` URLs | Non-admin restricted to `allowed_hosts` (YouTube only) |
| Live streams | Refused for non-admin (`duration is None`) |
| Track duration | Non-admin limited to `max_duration` (900s default) |
| Command prefix | Required for room messages; not required for IM |

### Rate limiting

| Mechanism | Scope | Default |
|-----------|-------|---------|
| Cooldown | Per-user, all commands | 3.0s |
| Request limit | Per-user, `play`/`request`/`req`/`p`/`เล่น` | 3 per 300s window |
| Max queue | Global | 50 requests |
| Max duration | Per-track, non-admin | 900s |
| Send interval | Global flood control | 1.5s |

## Supply chain

| Item | Status |
|------|--------|
| Dependencies | yt-dlp, mutagen, pyttsx3, pywinauto, pyperclip, PyInstaller |
| Version pinning | Not pinned in `pyproject.toml` (uses latest compatible) |
| CodeQL | Enabled in `.github/workflows/codeql.yml` |
| Dependabot | Configured for pip packages and GitHub Actions |
| Secret scanning | Not explicitly configured |
| SBOM | Generated for releases (CycloneDX) |
| Code signing | Self-signed or real cert via `build.ps1` |

## Recommendations

1. **Document the nickname spoofing limitation prominently** — Already done in README.md caveats and AUDIT.md O1. Ensure operators understand admin = display nick only.

2. **Keep `admins = []` default** — Already the case in `config.example.toml`. Operator must explicitly add their nick.

3. **Do not distribute `dist\` directory** — Already documented in README.md and AUDIT.md O7.

4. **Consider adding `auto_reply_interval` range validation** — Fixed (60s to 86400s).

5. **Consider audit logging for admin actions** — Currently all admin actions are logged via `log.info()`. Consider also announcing admin actions in the room for transparency.

## What is NOT tested (security limitations)

- Real Camfrog client (nickname spoofing cannot be tested without it)
- Real mpv (IPC pipe predictability cannot be tested without it)
- Windows-only code paths (UIA, winmsg, launcher, tts)
- Build/sign process (`build.ps1`)
