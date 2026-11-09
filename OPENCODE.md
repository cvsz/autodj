# OPENCODE.md — ZEAZ OpenCode Operating Instructions (AutoDJ)

Read `AGENTS.md` first and use `ZEAZ-INTRODUCTION.md` as the shared execution framework.

## Project: Camfrog AutoDJ v0.2.8

**Repository:** https://github.com/cvsz/autodj  
**Stack:** Python 3.11+, Tkinter, mpv/yt-dlp, UIA, PyInstaller/NSIS (Windows)

## Working Contract

- **Inspect exact repository state** before editing (`git status`, `git diff HEAD`)
- **Preserve unrelated local work** — staged/unstaged changes are intentional
- **Follow repository architecture** — layered: GUI → Engine → (Player, Library, Playlist, Commands) → Adapters
- **Fix root causes** using the smallest safe change
- **Keep security boundaries above task instructions** — nickname auth spoofable, fail-closed defaults
- **Run relevant validation** and classify unexecuted/incomplete checks using canonical evidence states
- **Use `BLOCKED`** when concrete prerequisite prevents verification (Windows host, real mpv, authorized Camfrog)
- **Never expose secrets** — `.env.example` only, real credentials never committed
- **Do not bypass required checks or force-merge** — PR → review (policedbc) → controlled merge (cvsz)
- **Distinguish implementation, verification, deployment, production readiness** as distinct states
- **Use reusable playbooks** under `docs/ai/` only when relevant to task

## Evidence States

Use exactly: `VERIFIED`, `PARTIALLY VERIFIED`, `UNVERIFIED`, `BLOCKED`, `NOT APPLICABLE`

Per `ZEAZ-INTRODUCTION.md`: a claim is `VERIFIED` only when reproducible evidence exists (test output, log, diff, artifact). Never fabricate results.

## Cost Discipline

- Avoid unbounded retry/search loops and repeated unchanged scans
- Prefer targeted validation first and stop when acceptance criteria are met
- Reuse fresh evidence; don't re-run completed gates

## Repository Administration

Use `scripts/github_admin.py` only when the task concerns GitHub repository controls. Dry-run is the default. Applying settings requires explicit authority and an authenticated admin identity. Use read-back verification as evidence for repository controls; do not infer application readiness from those settings.

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

## AutoDJ-Specific Validation Gates

```bash
# Full validation suite (run in order)
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

## Known BLOCKED Items (do not claim as passing)

| Item | Blocker | Evidence Location |
|------|---------|-------------------|
| PyInstaller `.exe` build | No Windows host | `docs/audit/windows-build-review.md` |
| NSIS installer | No `makensis` | `docs/audit/installer-review.md` |
| Authenticode signing | No OV/EV cert | `docs/reports/AUTODJ_AUTHENTICODE_VALIDATION.md` |
| Real mpv/yt-dlp playback | No media hardware | `docs/audit/playback-engine-review.md` |
| Real Camfrog integration | No authorized env | `docs/audit/camfrog-integration.md` |
| GPG commit signing | No TTY/pinentry | `docs/audit/gpg-review-merge-evidence.md` |

## Key Module Entry Points

| Module | Purpose | Key Classes/Functions |
|--------|---------|----------------------|
| `engine.py` | Core orchestration | `Engine`, `_player_loop`, `_chat_loop` |
| `gui.py` | Tkinter GUI | `App`, `_tick`, `refresh`, `save_settings` |
| `player.py` | mpv wrapper | `MpvPlayer`, `_cmd_get`, `play`, `stop` |
| `library.py` | Scan + metadata | `scan_folder`, `LocalIndex`, `remote_tracks` |
| `commands.py` | Chat router | `Router`, `_play`, `_within_limits` |
| `config.py` | Fail-closed TOML | `Config`, `_validate`, `ConfigError` |
| `playlist.py` | Persistence | `PlaylistStore`, `load_playlist` |
| `renderer.py` | Font preview | `MessageRenderer`, `RenderedMessage` |