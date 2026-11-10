# AGENTS.md — Repository Agent Contract (AutoDJ)

> **READ FIRST — Canonical organization-wide policy:** https://github.com/cvsz/zeaz/blob/main/zeaz.md (SUPER ULTRA AI ORC v2.1). This reference is required reading and takes precedence per Section 13.3 instruction precedence. Local rules below may be stricter but must not weaken mandatory security, safety, evidence, validation, or release requirements.

## Project: CamfrogAutoDJ

**Repository:** https://github.com/cvsz/autodj  
**Owner:** cvsz  
**Default branch:** main  
**Version:** 0.2.9 (Python 3.11+)  
**Description:** Music bot for Camfrog rooms — YouTube + local MP3/MP4 autoplay, `!commands`, now/next announcements, TTS, bilingual EN/TH GUI and chat.

---

## Purpose

This repository is a **production-ready DJ automation platform**, not a template. Changes must:
- Preserve audio correctness, GUI responsiveness, and playlist integrity
- Maintain cross-platform compatibility (Windows primary, Linux headless)
- Keep security boundaries (nickname auth spoofing documented, fail-closed defaults)
- Update documentation when behavior, config, or release procedures change

---

## Operating rules

- Read `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `ROADMAP.md`, and this `AGENTS.md` before editing
- Keep code, configuration, filenames, commit messages, and technical documentation in **English**
- Prefer the smallest reviewable change that satisfies the requested scope
- Never weaken CI, security scanning, dependency review, branch protections, or release controls
- Never commit credentials, tokens, private keys, production endpoints, personal data, or realistic secrets — use documented placeholders (`REPLACE_ME`, `%APPDATA%\CamfrogAutoDJ\...`)
- Do not invent project-specific owners, domains, deployment providers, package registries, cloud accounts, or credentials
- Reuse existing workflows and documents instead of creating overlapping alternatives
- Pin GitHub Actions permissions to least privilege; prefer maintained first-party/verified actions
- Treat external input, generated artifacts, PRs from forks, and dependency metadata as untrusted

---

## Audio Engine Rules (Critical)

- **One mpv process per track** — no shared state between tracks
- **IPC for control** — pause, resume, seek, volume via mpv JSON IPC (named pipe on Windows, Unix socket on Linux)
- **Graceful timeout** — `mpv_timeout` is a grace period (duration + timeout), never a hard cap
- **Hang detection** — poll at 0.5s; terminate → kill after grace period exceeded
- **Resource cleanup** — IPC log files removed on completion; `proc` reference cleared
- **No audio I/O on GUI thread** — all playback in background thread; GUI polls position via IPC

---

## GUI Concurrency Rules

- **Tkinter mainloop owns the window** — no blocking I/O on main thread
- **Cross-thread updates via `tk.after(0, ...)`** — all GUI mutations from workers use this
- **Reentrancy guards** — buttons disabled during async operations (`_loading_folder`, `_set_adding_state`)
- **Cancellation** — `stop_evt` propagated to all workers; `ThreadPoolExecutor.shutdown(cancel_futures=True)`
- **Timer cleanup** — `after_cancel` on window close for animation and poll timers

---

## Library Scanning Rules

- **Never follow symlinks** — `entry.is_symlink()` → `continue` (avoids cycles, reparse points, Windows junction hangs)
- **Bounded recursion** — `max_dirs` cap (default 50 for autoplay, 0 = unlimited for manual)
- **Bounded results** — `limit` cap on tracks returned (default 2000 GUI, 500 autoplay)
- **Permission resilience** — `PermissionError` caught per-entry; scan continues
- **Metadata fallback** — `mutagen` errors caught; fall back to filename

---

## Configuration Rules

- **Fail-closed validation** — `ConfigError` raised on any invalid value; exact line + `^` marker shown
- **Atomic writes** — temp file + `os.replace()` + `.bak` backup
- **Auto-relocation** — if config not writable (e.g., Program Files), write to `%APPDATA%\CamfrogAutoDJ\`
- **Nested dataclass** — `MessageStyle` for font/style (GUI preview only; Camfrog sends plain text)
- **Validation order** — type → choices → ranges → regexes → semantic (`_validate`)

---

## Security Rules

- **Nickname-based auth is spoofable** — documented in-code; fail-closed when `admins = []`
- **IM commands require room presence** — `im_require_room_presence = true` (default)
- **Blocked users silently ignored** — no error messages leaked
- **No `shell=True`** — all `subprocess` use argument lists
- **No unsafe deserialization** — `tomllib` (stdlib), `json` (stdlib); no `pickle`/`yaml.load`
- **Secrets never tracked** — `.env.example` only; real `.env` gitignored

---

## Review skill

- Use [Scrutinize](.agents/skills/scrutinize/SKILL.md) when asked to review, audit, sanity-check, or give a second opinion on a plan, PR, diff, design, or code change, or when invoked with `/scrutinize`
- Question whether the change is necessary or can be smaller before tracing real code paths and verifying behavioral claims
- Cite concrete file/line evidence and distinguish unverified claims from confirmed behavior

---

## Change workflow

1. Inspect the current exact branch/head and existing files
2. Identify the smallest missing or inconsistent capability
3. Add tests or validation first when practical
4. Implement without widening scope
5. Run the relevant validation and security checks
6. Update documentation when behavior, setup, governance, or release procedures change
7. Open a pull request; do not claim merge/release readiness without exact-head evidence

---

## Verification checklist (minimum)

- [ ] Markdown/YAML syntax for touched files
- [ ] Workflow permissions/triggers
- [ ] Links and placeholders resolve
- [ ] No committed secrets (`git ls-files | grep -E '(\.env|id_rsa|.*\.pem|.*\.key$)'`)
- [ ] Consistency between README, config.example.toml, CHANGELOG, docs/
- [ ] `python -m compileall -q camfrog_autodj tests tools`
- [ ] `python -m pytest -q -p no:faulthandler -p no:cacheprovider`
- [ ] `ruff check camfrog_autodj tests tools`
- [ ] `ruff format --check camfrog_autodj tests tools`
- [ ] `mypy camfrog_autodj`
- [ ] `shellcheck scripts/*.sh tools/*.sh`

---

## Pull requests and releases

PRs must state: scope, tests, security impact, compatibility/migration impact, documentation impact, deployment impact, and rollback plan.  
Releases require green required checks and explicit evidence; never infer production readiness from documentation alone.

---

## Security

Report vulnerabilities through `SECURITY.md`, not public issues. Security-related templates must redirect sensitive reports accordingly. Fail closed when a security-sensitive configuration is incomplete.

---

## Documentation ownership

- `.github/`: GitHub automation, community health, ownership, issue/PR templates
- `docs/`: versioned engineering, operations, release, repository-administration, rollout guidance
- `docs/audit/`: evidence-backed audit reports (30+ files)
- `docs/adr/`: architecture decision records
- `docs/protocols/`: reverse-engineering evidence (Camfrog font logic, UIA behavior)
- `docs/qualification/`: Windows qualification guides and evidence schemas
- Root Markdown files: repository-wide policy and project lifecycle guidance

---

## ZEAZ reusable execution layer

- Use `ZEAZ-INTRODUCTION.md` as the cross-agent execution framework
- Use `docs/ai/README.md` to select task-specific reusable prompts and playbooks
- Task playbooks are additive and never weaken this repository contract
- Use canonical evidence-state definitions: `VERIFIED`, `PARTIALLY VERIFIED`, `UNVERIFIED`, `BLOCKED`, `NOT APPLICABLE`
- Keep implementation, verification, deployment, and production readiness as distinct states

---

## Evidence-state decision rule

Per `ZEAZ-INTRODUCTION.md`: a claim is `VERIFIED` only when reproducible evidence exists (test output, log, diff, artifact). `BLOCKED` when a concrete prerequisite prevents verification (e.g., Windows host for PyInstaller). Never fabricate results.

---

## Existing-repository rollout

When applying this contract to an established repository, follow `docs/repository-rollout.md`. Audit the target first and port only missing compatible controls. Do not overwrite repository-specific AGENTS rules, CI matrices, release workflows, infrastructure ownership, or operational evidence merely to match this template.

For repository administration, `scripts/github_admin.py` requires an authenticated GitHub identity with Administration permission. Treat successful read-back verification—not script presence—as evidence that the controls are effective.

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