# CODEX.md — ZEAZ Codex Operating Instructions (AutoDJ)

Read `AGENTS.md` first. Use `ZEAZ-INTRODUCTION.md` as the shared execution framework.

## Project: CamfrogAutoDJ v0.2.8

**Repository:** https://github.com/cvsz/autodj  
**Type:** Production DJ automation platform (not template)  
**Stack:** Python 3.11+, Tkinter, mpv/yt-dlp, UIA  
**Platforms:** Windows (primary), Linux (headless/CI)

---

## Quick Reference

| File | Purpose |
|------|---------|
| `engine.py` | Core: Engine, player loop, chat loop, autoplay logic |
| `gui.py` | Tkinter GUI: App, animation, settings dialog, polling |
| `player.py` | mpv wrapper: IPC, play/stop, fade, position query |
| `library.py` | Scan/metadata: scan_folder, LocalIndex, remote_tracks |
| `commands.py` | Router: cooldown, rate limit, IM/room, admin/auth |
| `config.py` | Fail-closed TOML: Config, ConfigError, MessageStyle |
| `playlist.py` | Persistence: PlaylistStore, atomic JSON |
| `renderer.py` | Font/style preview: MessageRenderer, RenderedMessage |

---

## Operating Contract

1. **Inspect first** — `git status`, `git diff`, read target module
2. **Smallest safe change** — fix root cause, no scope creep
3. **Run validation** — pytest, ruff, mypy, compileall, shellcheck
4. **Evidence states** — `VERIFIED`/`PARTIALLY VERIFIED`/`UNVERIFIED`/`BLOCKED`/`NOT APPLICABLE`
5. **Never fabricate** — BLOCKED is honest, not failure
6. **Security first** — nickname auth spoofable, fail-closed, no shell=True

---

## AutoDJ-Specific Rules

### Audio Engine
- One mpv/track via `subprocess.Popen` + JSON IPC
- `mpv_timeout` = grace period (duration + timeout)
- Hang detection @0.5s; terminate → kill
- IPC logs cleaned; no leaks
- GUI polls position via IPC (`get_time_pos`) + wall-clock fallback

### GUI Concurrency
- Zero blocking on main thread
- All cross-thread via `tk.after(0, callback)`
- Reentrancy guards: `_loading_folder`, `_set_adding_state`
- Timers cancelled on close

### Library Safety
- **Never follow symlinks** — `is_symlink() → continue`
- Bounded: `max_dirs` (recursion), `limit` (tracks)
- Per-entry `PermissionError` caught
- `mutagen` errors → filename fallback

### Config
- Fail-closed `ConfigError` with line+column marker
- Atomic write: `.tmp` → `os.replace()` → `.bak`
- Auto-relocate to `%APPDATA%\CamfrogAutoDJ\`
- `MessageStyle` = GUI preview only (Camfrog = plain text)

### Security
- Nickname auth spoofable → documented, fail-closed (`admins = []`)
- IM requires room presence (`im_require_room_presence = true`)
- Blocked users silently ignored
- No `shell=True`, no `pickle`/`yaml.load`

---

## Validation Commands

```bash
# Full suite
python -m compileall -q camfrog_autodj tests tools
python -m pytest -q -p no:faulthandler -p no:cacheprovider
ruff check camfrog_autodj tests tools
ruff format --check camfrog_autodj tests tools
mypy camfrog_autodj
shellcheck scripts/*.sh tools/*.sh

# Security
git ls-files | grep -E '(\.env|id_rsa|.*\.pem|.*\.key$)'
git verify-commit HEAD
```

---

## BLOCKED Gates (Do Not Claim)

| Gate | Blocker | Evidence |
|------|---------|----------|
| PyInstaller `.exe` | Windows 11 + VS Build Tools | `docs/audit/windows-build-review.md` |
| NSIS installer | `makensis` + NSIS 3.0+ | `docs/audit/installer-review.md` |
| Authenticode sign | OV/EV cert + timestamp | `docs/reports/AUTODJ_AUTHENTICODE_VALIDATION.md` |
| Real mpv/yt-dlp | Hardware + media | `docs/audit/playback-engine-review.md` |
| Camfrog integration | Authorized test env | `docs/audit/camfrog-integration.md` |
| GPG signing | GPG_PASSPHRASE + TTY | `docs/audit/gpg-review-merge-evidence.md` |

---

## Change Workflow

1. `git status` — inspect exact state
2. Identify smallest missing capability
3. Add test/validation first
4. Implement minimal change
5. Run all validation gates
6. Update docs: `CHANGELOG.md`, `config.example.toml`, `messages.py`, manuals
7. PR → independent review (policedbc) → controlled merge (cvsz)

---

## Documentation Sync Checklist

When modifying behavior, update:
- [ ] `CHANGELOG.md` (Unreleased)
- [ ] `config.example.toml` (new keys)
- [ ] `messages.py` (EN + TH)
- [ ] `docs/autodj-commands.{en,th}.md`
- [ ] `docs/user-manual.{en,th}.md`
- [ ] `docs/admin-manual.{en,th}.md`
- [ ] Relevant `docs/audit/*.md`

---

## Key Invariants (Do Not Weaken)

- `engine.py`: `_player_loop` single-threaded; `_chat_loop` submits to executor
- `gui.py`: `refresh` @500ms, `_tick` @30fps; `save_settings` atomic + validated
- `player.py`: IPC for all control; `CREATE_NO_WINDOW` on Windows
- `library.py`: `scan_folder` never follows symlinks
- `commands.py`: IM play-only for non-admins; sliding window rate limit
- `config.py`: `_validate` order — type → choices → ranges → regex → semantic

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