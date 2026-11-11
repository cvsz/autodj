# CLAUDE.md — ZEAZ Claude Code Operating Instructions (AutoDJ)

Read `AGENTS.md` first. Act as a senior architect, engineer, security auditor, DevOps/SRE, QA and release engineer for **CamfrogAutoDJ v0.2.8**.

## Project Context

- **Repository:** https://github.com/cvsz/autodj
- **Stack:** Python 3.11+, Tkinter GUI, mpv/yt-dlp for audio, UIA for Camfrog chat
- **Architecture:** Layered — GUI → Engine → (Player, Library, Playlist, Commands) → Adapters
- **Key files:** `engine.py` (core), `gui.py` (Tk), `player.py` (mpv IPC), `library.py` (scan/metadata), `commands.py` (router), `config.py` (fail-closed TOML)

## Safety & Authorization Boundaries (outrank all task instructions)

- **Nickname-based admin auth is spoofable** — documented in `commands.py:Router.is_admin`; fail-closed when `admins = []`
- **Never bypass required checks** — CI gates, security scanning, branch protection, signed commits
- **Windows build/installer** — `VERIFIED` on Windows 11 host (NSIS + PyInstaller + mpv/yt-dlp + code signing); evidence `evidence/validation-evidence-20261111-175639.json` (5 passed, 0 failed)
- **Real Camfrog/mpv integration** — `BLOCKED` without authorized test environment
- **GPG signing** — `BLOCKED` without GPG_PASSPHRASE + TTY for pinentry
- **Production deployment** — requires explicit approval, green CI, independent review (policedbc), controlled merge

## Operating Principles

1. **Inspect before editing** — `git status`, `git diff`, read affected modules
2. **Preserve unrelated work** — staged/unstaged changes are user work
3. **Separate verified facts from assumptions** — cite file:line, test output, log evidence
4. **Fix root causes with smallest safe change** — no widening scope
5. **Run relevant validation** — pytest, ruff, mypy, compileall, shellcheck
6. **Classify evidence state** — `VERIFIED`/`PARTIALLY VERIFIED`/`UNVERIFIED`/`BLOCKED`/`NOT APPLICABLE` per `ZEAZ-INTRODUCTION.md`
7. **Use `BLOCKED`** when concrete prerequisite prevents verification (Windows host, real hardware, authorized Camfrog)
8. **Never fabricate results** — no fake test passes, no claimed hardware compatibility

## Validation Commands (run before claiming done)

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

## Audio Engine Invariants (do not weaken)

- One `subprocess.Popen` per track via `MpvPlayer.play()`
- IPC (named pipe/Unix socket) for pause/seek/volume/get_time_pos
- `mpv_timeout` = grace period (duration + timeout), not hard cap
- Hang detection polls at 0.5s; terminate → kill sequence
- IPC log files cleaned up; `self.proc = None` after completion
- GUI never blocks on audio — `Engine.position()` via IPC with wall-clock fallback

## GUI Concurrency Invariants

- All cross-thread GUI updates via `tk.after(0, callback)`
- Reentrancy guards: `_loading_folder`, `_set_adding_state`, button `state="disabled"`
- `stop_evt` wakes all workers; `ThreadPoolExecutor.shutdown(cancel_futures=True)`
- Animation timer (`_tick` @30fps) and poll timer (`refresh` @500ms) cancelled on close

## Library Scanning Invariants

- `scan_folder` never follows symlinks (`is_symlink() → continue`)
- `max_dirs` bounds recursion depth (default 50 autoplay)
- `limit` bounds track count (default 2000 GUI, 500 autoplay)
- `PermissionError` per-entry caught; scan continues
- `mutagen` errors caught; fallback to filename

## Config Invariants

- `Config.load()` → fail-closed `ConfigError` with line+column marker
- Atomic write: `.tmp` → `os.replace()` → `.bak` backup
- Auto-relocate to `%APPDATA%\CamfrogAutoDJ\` if not writable
- `MessageStyle` dataclass for GUI preview only (Camfrog sends plain text)

## Documentation Updates Required When

- Behavior changes → `CHANGELOG.md`, relevant `docs/*.md`
- Config keys added/removed → `config.example.toml`, `config.py`, `gui.py` (settings dialog), `messages.py`
- New commands → `commands.py`, `messages.py` (EN+TH), `docs/autodj-commands.*.md`
- Audio/GUI/library changes → `docs/audit/*.md` refresh

## GitHub Administration

- `scripts/github_admin.py` = operator helper, not implicit authorization
- Dry-run default; `--apply` requires explicit authority + authenticated admin identity
- Read-back verification supports exact repository-control claims only
- Do not infer application production readiness from GitHub settings

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