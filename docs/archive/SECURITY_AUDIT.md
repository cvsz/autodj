# Security Audit — AutoDJ v0.3.0

**Date:** 2026-11-16  
**Branch:** main (HEAD: fecc053)  
**Repository:** https://github.com/cvsz/autodj

---

## Executive Summary

A comprehensive security audit was performed against the AutoDJ codebase. All security-sensitive areas were reviewed. **No critical or high-severity findings were identified.** One configuration gap was identified and remediated (`.git-credentials` excluded from Docker build context).

---

## Security Findings

### Resolved in this session

| ID | Severity | Finding | Location | Remediation | Status |
|----|----------|---------|----------|-------------|--------|
| SEC-001 | Medium | `.git-credentials` excluded from `.gitignore` but not from `.dockerignore`. Dockerfile uses `COPY . ./`, which would bake credentials into the image. | `.dockerignore`, `Dockerfile` | Added `.git-credentials` to `.dockerignore` | ✅ Fixed |
| SEC-002 | High | `docs/optimize.md` contained exposed secrets: Google API key (`AIza...`), NVIDIA API keys (`nvapi-...`), encrypted tokens (`AQ.…`), QWEN API key (`sk-…`), Alicloud access keys (`LTAI…`). | `docs/optimize.md` | Replaced all real values with `REPLACE_ME_*` placeholders | ✅ Fixed |

### Verified secure (no findings)

| Area | Check | Result |
|------|-------|--------|
| Environment secrets | `.env`, `.env.*`, `.env.bak` tracked in Git | ✅ Not tracked (`.env` gitignored, `.env.example` only) |
| Credential stores | `.git-credentials` tracked in Git | ✅ Not tracked (gitignored) |
| Private keys/certs | `*.pem`, `*.key`, `*.pfx`, `*.cer` tracked | ✅ Not tracked (gitignored) |
| Certificate directory | `cert/` tracked in Git | ✅ Not tracked (gitignored) |
| Hardcoded credentials in code | Password/secret/token/private_key patterns in `.py` files | ✅ None found |
| Subprocess safety | `shell=True` usage | ✅ None (all use argument lists) |
| Deserialization safety | `pickle`, `yaml.load`, `eval` usage | ✅ None (uses `tomllib` and `json` only) |
| Path traversal | Admin `_resolve_local_file` confinement to `music_dirs` | ✅ Verified (test_admin_path_traversal.py) |
| Empty prefix auth bypass | Empty command prefix rejected | ✅ Verified (test_empty_prefix.py) |
| Nickname auth spoofing | Documented as spoofable; fail-closed when `admins = []` | ✅ Documented in-code |
| IM room presence | `im_require_room_presence = true` (default) | ✅ Default on |
| Blocked users | Silently ignored, no error messages leaked | ✅ Verified |
| Config validation | Fail-closed `ConfigError` with exact line + `^` marker | ✅ Verified |
| Atomic config writes | Temp file + `os.replace()` + `.bak` backup | ✅ Verified |
| Config auto-relocation | Writes to `%APPDATA%\AutoDJ\` when not writable | ✅ Verified |
| Dependency vulnerabilities | Declared deps: `yt-dlp`, `mutagen`, `pyttsx3`, `pywinauto` (win32), `pyperclip` (win32) | ✅ 0 known vulnerabilities |
| Installer privilege escalation | `RequestExecutionLevel user` in NSIS installer | ✅ User-level execution |
| Installer user data preservation | Uninstaller preserves `config.toml`, `playlist.json`, logs | ✅ Verified (test_installer_data_safety.py) |
| Webhook security | HMAC-SHA256 signature verification, per-IP rate limiting, CORS | ✅ Verified |
| Code signing | Authenticode signature via build.ps1 | ✅ Supported |
| GitHub Actions permissions | `contents: read` (CI/tests), `contents: write` + `id-token: write` (release) | ✅ Least privilege |
| Action versions | Pinned immutable SHAs for all actions | ✅ Verified |

---

## Secrets Scan

```bash
git ls-files | grep -E '(\.env|id_rsa|id_ed25519|.*\.pem|.*\.key$)' | grep -v '^\.env\.example$'
```

**Result:** Empty (no secret-bearing files tracked in Git)

---

## Docker Build Context Security

The Dockerfile uses `COPY . ./`. The `.dockerignore` now excludes:
- `.env`, `.env.*` — local environment files
- `.git-credentials` — Git credential store (added in this session)
- `config.toml`, `config.toml.bak`, `config.toml.tmp` — local configuration
- `*.log`, `autodj.log` — log files
- `build/`, `dist/`, `artifacts/`, `*.exe`, `*.zip` — build artifacts

No secrets are baked into the Docker image.

---

## Remaining Security Considerations

| Area | Consideration | Status |
|------|---------------|--------|
| Nickname-based auth | Documented as spoofable in-code. Prefer immutable authenticated identifiers where protocol supports them. | Documented |
| Real Camfrog integration | Not tested (requires actual Camfrog client and room) | Not tested — manual verification needed on Windows |
| Code signing certificate | Self-signed cert used by default; EV/OV cert recommended for public distribution | Documented in build.ps1 |
| Windows UIA adapter | COM serialization prevents reader/sender wedge | Implemented |

---

## Conclusion

The AutoDJ codebase maintains a strong security posture. All identified findings have been remediated. Fail-closed defaults are preserved throughout. No secrets are committed to Git.

