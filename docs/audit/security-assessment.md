# Security Assessment — CamfrogAutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`  
**Policy reference:** SECURITY.md, GOVERNANCE.md, AGENTS.md  
**Status:** Reviewed; no Critical or High unresolved findings

## Authorization model

- Admin authorization is nickname-based (`commands.py:Router.is_admin`). The code documents explicitly: "Nickname-based authorization is spoofable — any user can adopt an operator's nick and gain admin privileges." Fail-closed: an empty `admins` list grants no nickname-based admin access. `msg.local` (console) is trusted only for local/dev execution.
- Blocked users (`blocked_users` config, `block`/`unblock` commands) are ignored silently; admins cannot be blocked.
- This is an inherent limitation of a nickname-based chat bot; documented rather than concealed.

## Input validation

- `config.py:Config` validates types, ranges, allowed choices, and regexes for every setting; unknown keys produce a "did you mean" hint; invalid values raise explicit `ConfigError`.
- `playlist.py:_is_valid_source` validates playlist entries (http(s) URL, `ytsearchN:` query, or local path); invalid entries are skipped with a warning, never silently deleted.
- `commands.py:_remove` guards against Unicode-digit bypass (`"²".isdigit()` but `int("²")` raises).
- `library.py:host_ok` confrains non-admin YouTube requests to `allowed_hosts` (youtube.com, youtu.be, music.youtube.com) with subdomain matching.

## Subprocess / command execution

- All subprocess calls use argument lists (`shell=False` never used). Ruff `S108`/`S307`/`S608` (shell=True) are ignored by policy because they are never used.
- `launch.py:_start` uses `subprocess.Popen([exe])` (list, not shell).
- `library.py:_extract_exe` and `doctor.py:_ytdlp_version` use `subprocess.run([...], ...)` with `CREATE_NO_WINDOW` on Windows, `capture_output`, and timeouts.
- `player.py:play` builds an argument list for mpv; never a shell string.

## Secrets / credentials

- No credentials, tokens, or private keys committed (CI `ci.yml` checks for tracked `.env`, `id_rsa`, `*.pem`, `*.key`).
- `.git-credentials` exists at `/home/cvsz/.git-credentials` (mode 600, owned by cvsz). It was **not** read, not printed, not committed, and not logged. Git credential helper configuration was inspected only for existence/permissions.
- `config.toml`, `config.toml.bak`, `config.default.toml`, `config.example.toml` are present; none contain real secrets (placeholders only).
- Certificate: `cert/autodj-codesign.cer` is a public cert (no private key).

## Cryptography

- yt-dlp certificate verification is always preserved; never disabled. Custom CA bundle supported via `certifi.where()` patching (module path) — verification stays on.
- mpv download over HTTPS in CI workflows.
- Code signing: self-signed or real cert via `build.ps1` with RFC 3161 timestamping. Signing key availability is not claimed unless verified (BLOCKED here — no Windows/signing host).

## Audit trail

- `engine.py` logs every track state transition, chat line (incoming/outgoing), delivery attempt, and request with IDs (`req=`, `deliv=`) for correlation.
- Chat message text is truncated to 80 chars in delivery logs (`log_delivery`) to avoid logging full private content.
- `log_chat` writes to both in-memory `chat_log` and the logger (`--log-file`).

## Unresolved items

- GPG signing of commits could not be performed in this environment (`GPG_PASSPHRASE` unset, no TTY). Reported as a blocker (F-005), not faked.
- Windows Authenticode signature verification could not be performed (no Windows host). Not claimed as verified.
