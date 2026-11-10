# KILO.md — ZEAZ Kilo Code Operating Instructions (AutoDJ)

Read `AGENTS.md` first. Use `ZEAZ-INTRODUCTION.md` as the shared execution framework.

## Project: CamfrogAutoDJ v0.2.8

**Repository:** https://github.com/cvsz/autodj  
**Primary:** Windows (Camfrog) | **Secondary:** Linux (headless/CI)  
**Language:** Python 3.11+  
**GUI:** Tkinter (custom dark studio theme, 30fps animation)  
**Audio:** mpv + yt-dlp (IPC control, fade in/out, dynaudnorm)  
**Chat:** UIA (Windows) / Logtail / Console (adapters)

---

## Mission

Transform AutoDJ into a **complete, stable, reliable, high-performance, production-ready DJ automation platform** with:
- Real-time music playback from YouTube + local library
- Bilingual (EN/TH) chat commands and GUI
- Admin controls, queue management, autoplay, TTS
- Secure, auditable, independently reviewed releases

---

## Operating Rules (AutoDJ-Specific)

### 1. Audio Correctness First
- One mpv process per track — no shared state
- IPC for all control (pause, seek, volume, position)
- `mpv_timeout` = grace period, never hard cap
- Hang detection @0.5s poll; terminate → kill sequence
- IPC logs cleaned up; no FD/process leaks

### 2. GUI Responsiveness Non-Negotiable
- Zero blocking I/O on Tk main thread
- All worker→GUI via `tk.after(0, callback)`
- Reentrancy guards on all async buttons
- Timers cancelled on close (`after_cancel`)

### 3. Library Safety
- **Never follow symlinks** — prevents cycles, reparse points, junction hangs
- Bounded recursion (`max_dirs`) and results (`limit`)
- Per-entry `PermissionError` caught; scan continues
- Metadata errors → fallback to filename

### 4. Config Integrity
- Fail-closed validation with exact line+column error
- Atomic writes (tmp + replace + .bak)
- Auto-relocate to `%APPDATA%\CamfrogAutoDJ\` if needed
- Nested `MessageStyle` for GUI preview only

### 5. Security Boundaries
- Nickname auth spoofable — documented, fail-closed
- IM commands require room presence (default on)
- Blocked users silently ignored
- No `shell=True`, no unsafe deserialization

---

## Evidence States (Canonical)

| State | When to Use |
|-------|-------------|
| `VERIFIED` | Reproducible evidence: test output, log, diff, artifact |
| `PARTIALLY VERIFIED` | Some evidence, gaps documented |
| `UNVERIFIED` | No evidence yet, not blocked |
| `BLOCKED` | Concrete prerequisite missing (Windows host, real hw, auth env) |
| `NOT APPLICABLE` | Feature not in scope |

**Never fabricate.** `BLOCKED` is honest, not failure.

---

## Validation Gates (Run Before Claiming Done)

```bash
# Python
python -m compileall -q camfrog_autodj tests tools
python -m pytest -q -p no:faulthandler -p no:cacheprovider
ruff check camfrog_autodj tests tools
ruff format --check camfrog_autodj tests tools
mypy camfrog_autodj

# Shell
shellcheck scripts/*.sh tools/*.sh

# Security
git ls-files | grep -E '(\.env|id_rsa|.*\.pem|.*\.key$)'
git verify-commit HEAD
```

---

## BLOCKED Gates (Do Not Claim Passing)

| Gate | Blocker | Tracking |
|------|---------|----------|
| PyInstaller build | Windows 11 + VS Build Tools | `docs/audit/windows-build-review.md` |
| NSIS installer | `makensis` + NSIS 3.0+ | `docs/audit/installer-review.md` |
| Authenticode sign | OV/EV cert + timestamp | `docs/reports/AUTODJ_AUTHENTICODE_VALIDATION.md` |
| Real audio playback | mpv + yt-dlp + media files | `docs/audit/playback-engine-review.md` |
| Camfrog integration | Authorized Camfrog env | `docs/audit/camfrog-integration.md` |
| GPG signing | GPG_PASSPHRASE + TTY | `docs/audit/gpg-review-merge-evidence.md` |

---

## Key Architectural Invariants

### Engine (`engine.py`)
- `ThreadPoolExecutor(8)` for lookups; player loop single-threaded
- `_chat_loop` → `Router.handle` submitted to executor
- `_player_loop` → `_play_one_track` with retry/backoff
- `stop_evt` wakes all; shutdown joins threads (5s timeout)

### GUI (`gui.py`)
- `_tick` @33ms (30fps) for animation; `refresh` @500ms for data
- `snapshot()` → thread-safe data; `chat_snapshot()` → thread-safe chat
- Settings dialog: atomic save, validation, auto-relocation

### Player (`player.py`)
- `MpvPlayer.play()` → IPC + grace period + hang detection
- `_cmd_get()` for `time-pos` (accurate position)
- `CREATE_NO_WINDOW` on Windows; no console flash

### Library (`library.py`)
- `scan_folder` recursive, symlink-safe, bounded
- `LocalIndex` builds track list at startup
- `remote_tracks` → yt-dlp (exe preferred, module fallback)

### Commands (`commands.py`)
- `Router` with cooldown + sliding window rate limit
- IM: no prefix, room presence required, admin works
- Room: prefix required, play IM-only for non-admins

---

## Documentation Maintenance

When changing behavior, update:
- `CHANGELOG.md` (Unreleased section)
- `config.example.toml` (new keys with comments)
- `messages.py` (EN + TH strings)
- `docs/autodj-commands.{en,th}.md`
- `docs/user-manual.{en,th}.md`
- `docs/admin-manual.{en,th}.md`
- Relevant `docs/audit/*.md` (refresh evidence)

---

## Release Procedure

1. All validation gates green (or honestly BLOCKED)
2. Independent review by `policedbc` (exact HEAD SHA)
3. GPG-signed commit by `cvsz`
4. Controlled merge: `gh pr merge --match-head-commit <SHA>`
5. Post-merge verification on `main`
6. Tag release with evidence bundle

---

## GitHub CLI Workflow (cvsz ↔ policedbc)

### Credentials & GPG

- **Git credentials:** `/home/cvsz/.git-credentials` (never expose contents)
- **GPG signing:** `commit.gpgsign=true`, `gpg.program=/home/cvsz/.local/bin/gpg-loopback.sh`
- **GPG key:** `cvsz <seaza@msn.com>` (key `515DB3BD9BF14AA6646AC6770C54E869DE49D872`)

### Phase A — Developer (cvsz): Implement & Open PR

```bash
# Authenticate as cvsz
gh auth switch -u cvsz
gh auth status  # verify: active account cvsz

# Git identity
git config user.name "cvsz"
git config user.email "seaza@msn.com"

# Create feature branch
git checkout -b feat/autodj-<feature-name>

# Develop: fix bugs, add features, update docs
# Run validation gates
python -m pytest -q -p no:faulthandler -p no:cacheprovider
ruff check camfrog_autodj tests tools
ruff format --check camfrog_autodj tests tools
mypy camfrog_autodj

# GPG-signed commit
git add -A
git commit -S -m "feat: <description>

<details>"

# Push branch
git push origin feat/autodj-<feature-name>

# Open PR as cvsz
gh pr create --title "feat: <description>" --body "<body>" --base main
# PR must state: scope, tests, security impact, compat/migration, docs, deployment, rollback
```

### Phase B — Independent Reviewer (policedbc): Audit & Approve

```bash
# Switch to reviewer identity
gh auth switch -u policedbc
gh auth status  # verify: active account policedbc

# Review exact HEAD SHA (no new commits after approval)
gh pr view <PR_NUMBER> --json headRefOid --jq .headRefOid
# Verify: pytest, ruff, mypy, format all pass
# Verify: git verify-commit <HEAD_SHA> → Good signature

# Approve (not self-approval — cvsz authored)
gh pr review <PR_NUMBER> --approve --body "Independent review: <summary>"
# Check: reviewDecision=APPROVED, author=policedbc
```

### Phase C — Developer (cvsz): Controlled Merge

```bash
# Switch back to cvsz
gh auth switch -u cvsz
gh auth status

# Pre-merge verification
# - policedbc APPROVAL for exact HEAD SHA ✓
# - No new commits after approval ✓
# - CI/local validation green ✓
# - Mergeable, open, not draft ✓
# - No unresolved Critical/High findings ✓

# Merge with exact head commit enforcement
gh pr merge <PR_NUMBER> --merge --match-head-commit <EXPECTED_HEAD_SHA>
# Exit 0; PR state MERGED, merge commit SHA recorded

# Post-merge verification
git fetch origin
git checkout main
git pull origin main  # fast-forward
# Verify: code present on main, pytest 336 pass, ruff clean
```

### Rules

- **Never** force-push, bypass branch protection, self-approve, merge with pending checks
- **Never** commit directly to main — all changes via PR
- **Always** verify exact HEAD SHA before merge (`--match-head-commit`)
- **GPG signing required** for merge commit and feature commits
- **Credential reference:** `/home/cvsz/.git-credentials` — never print or expose