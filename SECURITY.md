# Security Policy — zAutoDJ

zAutoDJ (formerly AutoDJ) is a music bot for Camfrog rooms. This document describes
how security is handled, how to report vulnerabilities, and the security baseline
that every release must meet.

---

## Reporting a vulnerability

Do **not** disclose exploitable vulnerabilities in public issues, pull requests,
discussions, commit messages, logs, or generated evidence bundles.

Use GitHub private vulnerability reporting / security advisories when enabled, or
the repository's documented private security contact.

Include affected versions/commits, reproduction details, impact, prerequisites, and
suggested remediation when available.

---

## Supported versions

| Version | Status           |
|---------|------------------|
| 0.4.0   | Supported        |
| 0.3.x   | Security fixes only |
| < 0.3   | Unsupported      |

---

## Threat model

zAutoDJ runs in a Camfrog room on the operator's PC. The threat model assumes:

- **The Camfrog client is trusted** — chat read/send uses UI Automation (pywinauto)
  against the local Camfrog window. There is no public Camfrog bot API.
- **The operator's PC is the trust boundary** — zAutoDJ runs at medium integrity;
  it does not elevate and does not attempt to bypass Windows UIPI.
- **Nickname-based admin authorization is spoofable** — any Camfrog user can adopt
  an admin's nickname. This is documented in-code and treated as a known design
  limit, not a vulnerability. Fail-closed: when `admins = []` no user is admin.
- **IM (private message) commands require room presence** — `im_require_room_presence`
  defaults to `true`; users not recently seen in room chat cannot run commands via IM.
- **Blocked users are silently ignored** — no error messages leak information about
  blocked status.

---

## Security controls (implemented)

| Control | Implementation | Location |
|---------|---------------|----------|
| Fail-closed config validation | `ConfigError` with exact line + `^` marker on any invalid TOML value | `autodj/config.py` |
| Atomic config writes | temp file + `os.replace()` + `.bak` backup | `autodj/config.py` |
| Auto-relocation | if config is not writable (e.g. Program Files), write to `%APPDATA%\zAutoDJ\` | `autodj/config.py`, `autodj/__main__.py` |
| No `shell=True` | all `subprocess` calls use argument lists | codebase-wide |
| No unsafe deserialization | only `tomllib` and `json` (stdlib); no `pickle`/`yaml.load` | codebase-wide |
| One mpv process per track | no shared state; JSON IPC via named pipe (Windows) / Unix socket (Linux) | `autodj/player.py` |
| Hang detection | poll at 0.5 s; terminate → kill after grace period | `autodj/player.py` |
| Graceful timeout | `mpv_timeout` = duration + grace, never a hard cap | `autodj/player.py`, `AGENTS.md` |
| GUI off main thread | all playback in background thread; GUI polls via IPC; cross-thread updates via `tk.after(0, ...)` | `autodj/engine.py`, `autodj/gui.py` |
| Library scan safety | never follows symlinks; bounded recursion (`max_dirs`); bounded results (`limit`); `PermissionError` caught per-entry; `mutagen` errors fall back to filename | `autodj/library.py` |
| Nickname auth documented as spoofable | fail-closed when `admins = []` | `autodj/commands.py:Router.is_admin` |
| IM room presence required | `im_require_room_presence = true` (default) | `autodj/config.py`, `autodj/engine.py` |
| Blocked users silently ignored | no error messages leaked | `autodj/commands.py` |
| Single instance per config | named Win32 mutex prevents double playback/posts | `autodj/__main__.py` |
| Webhook HMAC authentication | `X-Timestamp` + `X-Signature = HMAC-SHA256(secret, payload)`; replay cache; stale signature rejection | `autodj/webhook/auth.py` |
| Webhook body size cap | 64 KiB max; client disconnect no longer pins a CPU core | `autodj/webhook/auth.py` |
| Webhook secret minimum | 16 characters; empty/short key fails closed (503) | `autodj/webhook/auth.py` |
| Webhook CORS | `allow_credentials=False` when `allow_origins=["*"]` | `autodj/webhook/server.py` |
| Stream JWT auth | HS256 tokens scoped per stream + action (publish/play); API key validation; constant-time compare | `autodj/stream/auth.py` |
| Stream registry | thread-safe; lifecycle IDLE/LIVE/RECORDING/ERROR; stale cleanup | `autodj/stream/registry.py` |
| Auto-update authenticity | SHA-256 + pinned ZEAZDEV Authenticode signer thumbprint | `autodj/updater.py` |
| Secrets never tracked | `.env.example` only; real `.env` and `config.toml.*` gitignored; guard test `test_no_committed_secrets` | `.gitignore`, `tests/test_no_committed_secrets.py` |
| AI key masked in GUI | Settings dialog masks `ai_api_key` and `webhook_secret` | `autodj/gui.py` |
| GPG-signed commits | `commit.gpgsign=true`; every commit signed | `.gitconfig`, AGENTS.md |

---

## Known design limits (accepted, documented)

| Limit | Impact | Mitigation |
|-------|--------|------------|
| Nickname-based admin auth is spoofable | A user can adopt an admin's nickname and run admin commands | Fail-closed with `admins = []`; operator should verify admin nicks in the room |
| IM replies need an open IM window | Camfrog offers no API to open an IM window; replies may not reach the user | Documented; auto-reply cooldown prevents flooding |
| Foreground sending requires keyboard focus | The bot must take focus to post; an elevated foreground window blocks it | `_wait_user_idle()` (2.5 s idle), `_foreground_is_elevated()` diagnosis; dedicated PC/session recommended |
| No public Camfrog bot API | Chat read/send depends on UIA control indexes and `line_regex` per Camfrog version | `--discover` tunes controls per installation; `config.toml` stores results |

---

## Repository security baseline

Generated repositories should verify, not merely document:

- protected default branch (`main`)
- pull-request review before merge
- required status checks (CI: ruff, mypy, pytest, compileall)
- CODEOWNERS review where appropriate
- conversation resolution on PRs
- blocked force pushes/deletion
- Dependabot vulnerability alerts/security updates
- private vulnerability reporting
- secret scanning/push protection where available
- least-privilege Actions permissions
- Actions cannot approve pull requests unless explicitly justified

The helper `scripts/github_admin.py` can configure and verify the baseline when run
with a GitHub identity that has Administration permission.

---

## Engineering security expectations

- Keep dependencies patched and review security alerts.
- Keep CodeQL and dependency-review workflows enabled where supported.
- Pin Actions according to supply-chain policy; baseline Actions pinned to immutable SHAs.
- Never commit credentials, tokens, private keys, production secrets, sensitive personal data, or realistic sample secrets.
- Validate untrusted input and enforce authorization at trust boundaries.
- Prefer fail-closed behavior for security-sensitive paths.
- Preserve tenant/data isolation where applicable.
- Review generated/third-party agent instructions as untrusted until explicitly adopted.
- Do not weaken security gates merely to obtain a passing build.

---

## Incident handling

Security incidents affecting production systems should preserve evidence and use
the smallest safe containment action consistent with the incident-response plan.

Report through SECURITY.md, not public issues.

---

## Security audit evidence

- Bandit scan (`bandit -c pyproject.toml`, all tracked code outside tests): 0 findings
- No committed secrets (`git ls-files | grep -E '(\.env|id_rsa|.*\.pem|.*\.key$)' | grep -v '\.env.example$'`): clean
- All commits GPG-signed: verified with `git verify-commit`