# Security Assessment — cvsz/autodj

## Repository controls

| Control | State | Evidence |
|---------|-------|----------|
| CODEOWNERS independent review | Enforced | `.github/CODEOWNERS` + root `CODEOWNERS`; `@policedbc` for `.github/`, workflows, `SECURITY.md`, `AGENTS.md`, installer/build scripts, config |
| Branch protection | Documented | `scripts/github_admin.py --verify` (requires `gh` admin auth → BLOCKED in this env, not assumed) |
| Dependabot (pip + GH Actions) | Enabled | `.github/dependabot.yml` |
| CodeQL (Python) | Enabled | `.github/workflows/codeql.yml` (v4.39.1 pinned) |
| Dependency review | Enabled on PR | `.github/workflows/dependency-review.yml` |
| Secret scanning / push protection | Documented | `SECURITY.md`; private vulnerability reporting path |
| Least-privilege `GITHUB_TOKEN` | Documented | workflows use `contents: read`, `pull-requests: write`, `issues: write` only where needed |
| Actions cannot approve PRs | Documented | no `gh`/token-based auto-approval in workflows |
| Pinned action SHAs | Enforced | `fix/pin-actions-shas` (#83); all workflows use immutable SHAs |

## Application security

- **Authorization is nickname-based and spoofable.** `commands.Router.is_admin()` documents this explicitly: "Nickname-based authorization is spoofable — any user can adopt an operator's nick." Fail-closed: empty `admins` → no nickname-based admin access. Local/console (`msg.local`) trusted only for local/dev execution.
- **No hardcoded credentials.** `git grep` for tokens/keys → 0 matches; no tracked secret-bearing files.
- **Config secrets not logged.** `Engine.log_delivery` truncates text to 80 chars; never logs full private content.
- **Command execution safety:** all subprocess calls use argument lists; no `shell=True`; `os.startfile` (Windows URI launcher) `# noqa: S606`.
- **Path traversal:** `commands._load` rejects absolute paths outside `music_dirs`; `engine._resolve_local_file` requires admin for folders and `index.contains` for files.
- **Rate limits / flood control:** cooldown, per-user sliding-window request limit (`user_request_limit`/`rate_limit_window`), `max_queue`, `max_requests_per_user`, `send_interval`, `max_msg_len`, `max_duration`, `voteskip_threshold`.
- **Symlink / reparse-point safety:** `scan_folder` never follows symlinks; `limit`/`max_dirs` caps.
- **No silent overwrite of original media:** downloads/metadata are read-only; local files never modified.
- **Certificate verification preserved:** yt-dlp TLS never disabled; custom CA bundle supported via module path.

## Residual risks (documented)

- Nickname-based admin auth is spoofable on Camfrog (no immutable account identifier in UIA chat). Mitigation: fail-closed admin list, operator must set real `admins`.
- UIA chat reader depends on Camfrog window/control indexes; `line_regex` must be tuned per Camfrog version (documented caveat in README).
- Background chat send (`send_mode=background`) cannot prove the page accepted the message; `send_mode=auto` verifies appearance in room.

## Conclusion

No unresolved Critical or High security findings. Security baseline documented and enforced via CODEOWNERS, Dependabot, CodeQL, dependency review, pinned actions, fail-closed auth, and secret hygiene.
