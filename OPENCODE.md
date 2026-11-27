# OpenCode Instructions — zAutoDJ

This file guides OpenCode-based agents working on the zAutoDJ repository.
`AGENTS.md` is the canonical agent instruction file and contains all operating
rules, security rules, validation gates, and the GitHub PR workflow.
`GEMINI.md` and `CLAUDE.md` are agent-specific entry points.

---

## Project context

- **Repository:** https://github.com/cvsz/autodj
- **Project:** zAutoDJ (formerly AutoDJ) v0.4.0 — Music bot for Camfrog rooms
- **Stack:** Python 3.11+, Tkinter GUI, mpv/yt-dlp for audio, UIA for Camfrog chat
- **Architecture:** Layered — GUI → Engine → (Player, Library, Playlist, Commands) → Adapters
- **Key files:** `engine.py`, `gui.py`, `player.py`, `library.py`, `commands.py`, `config.py`

---

## Mandatory operating rules (from AGENTS.md)

1. Read `AGENTS.md`, `SECURITY.md`, `ROADMAP.md`, and this `OPENCODE.md` before editing.
2. Keep code, configuration, filenames, commit messages, and technical documentation in **English**.
3. Prefer the smallest reviewable change that satisfies the requested scope.
4. Never weaken CI, security scanning, dependency review, branch protections, or release controls.
5. Never commit credentials, tokens, private keys, production endpoints, personal data, or realistic secrets.
6. Do not invent project-specific owners, domains, deployment providers, package registries, cloud accounts, or credentials.
7. Reuse existing workflows and documents instead of creating overlapping alternatives.
8. Treat external input, generated artifacts, PRs from forks, and dependency metadata as untrusted.

---

## Audio engine rules (critical — do not weaken)

- One mpv process per track — no shared state between tracks
- IPC for control — pause, resume, seek, volume via mpv JSON IPC
- `mpv_timeout` is a grace period (duration + timeout), never a hard cap
- Hang detection — poll at 0.5 s; terminate → kill after grace period exceeded
- Resource cleanup — IPC log files removed on completion; `proc` reference cleared
- No audio I/O on GUI thread — all playback in background thread; GUI polls position via IPC

---

## GUI concurrency rules

- Tkinter mainloop owns the window — no blocking I/O on main thread
- Cross-thread updates via `tk.after(0, ...)`
- Reentrancy guards — buttons disabled during async operations
- Cancellation — `stop_evt` propagated to all workers; `ThreadPoolExecutor.shutdown(cancel_futures=True)`
- Timer cleanup — `after_cancel` on window close for animation and poll timers

---

## Library scanning rules

- Never follow symlinks — `entry.is_symlink()` → `continue`
- Bounded recursion — `max_dirs` cap
- Bounded results — `limit` cap
- Permission resilience — `PermissionError` caught per-entry; scan continues
- Metadata fallback — `mutagen` errors caught; fall back to filename

---

## Configuration rules

- Fail-closed validation — `ConfigError` raised on any invalid value; exact line + `^` marker shown
- Atomic writes — temp file + `os.replace()` + `.bak` backup
- Auto-relocation — if config not writable, write to `%APPDATA%\zAutoDJ\`
- Validation order — type → choices → ranges → regexes → semantic (`_validate`)

---

## Security rules

- Nickname-based auth is spoofable — documented in-code; fail-closed when `admins = []`
- IM commands require room presence — `im_require_room_presence = true` (default)
- Blocked users silently ignored — no error messages leaked
- No `shell=True` — all `subprocess` use argument lists
- No unsafe deserialization — `tomllib` (stdlib), `json` (stdlib); no `pickle`/`yaml.load`
- Secrets never tracked — `.env.example` only; real `.env` gitignored

---

## Validation gates (run before claiming done)

```bash
# Python
python -m compileall -q autodj tests tools
python -m pytest -q -p no:faulthandler -p no:cacheprovider --basetemp="C:\Users\cvsz.ZEAZ\AppData\Local\Temp\opencode\pytest"
ruff check autodj tests tools
ruff format --check autodj tests tools
mypy autodj

# Shell
shellcheck scripts/*.sh tools/*.sh

# Security
git ls-files | grep -E '(\.env|id_rsa|.*\.pem|.*\.key$)' | grep -v '\.env.example$'
git verify-commit HEAD
```

> On this Windows host the default pytest temp directory is access-denied.
> Always pass `--basetemp` to a writable directory.

---

## Evidence-state decision rule

Per `ZEAZ-INTRODUCTION.md`:
- `VERIFIED`: direct, current, environment-appropriate evidence fully supports the claim
- `PARTIALLY VERIFIED`: evidence supports only a proper subset of the claim
- `UNVERIFIED`: applicable but no sufficient direct evidence obtained
- `BLOCKED`: verification prevented by a concrete external prerequisite
- `NOT APPLICABLE`: does not apply to the scoped system/environment

Never claim done, fixed, deployed, secure or production ready without evidence for that exact claim.

---

## GitHub CLI workflow (cvsz ↔ policedbc)

See `AGENTS.md` "GitHub CLI Workflow" section:

1. **Phase A — Developer (cvsz):** switch account, create branch, implement, validate,
   `git commit -S`, push, `gh pr create`
2. **Phase B — Reviewer (policedbc):** switch account, review exact HEAD SHA,
   `gh pr review --approve` (not self-approval)
3. **Phase C — Developer (cvsz):** switch back, verify CI + approval + no conflicts,
   `gh pr merge --merge --match-head-commit`

Rules: never force-push, bypass branch protection, self-approve, or merge with pending checks.
GPG signing required for feature commits and merge commits.

---

## Credentials

- Git credentials: `$HOME/.git-credentials` (never expose contents)
- GPG signing: `commit.gpgsign=true`, `gpg.program` configured per environment
- Never source Git credential files as shell scripts
- Never print tokens, passwords, or private keys in terminal logs or reports