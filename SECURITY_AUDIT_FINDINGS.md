# Security Audit Findings - autodj

Date: 2026-11-16
Scanner: CodeQL

| Rule ID | Severity | File | Line | Status |
|---------|----------|------|------|--------|
| py/clear-text-storage-sensitive-data | High | camfrog_autodj/gui.py | 3293 | OPEN |
| py/clear-text-storage-sensitive-data | High | camfrog_autodj/gui.py | 3280 | OPEN |
| py/stack-trace-exposure | Medium | camfrog_autodj/webhook/server.py | 163 | OPEN |

## Finding 1: py/clear-text-storage-sensitive-data (High) - gui.py:3293

**Root cause:** Config file written to disk in plain text via `tmp.write_text(new_text, "utf-8")`. This can expose sensitive configuration values such as webhook_secret.

**Fix:** Encrypt sensitive configuration values before writing to disk, or use environment variables for secrets.

**Fix applied:** Moved sensitive config values (webhook_secret) to environment variable resolution at load time, removed from persistent storage.

## Finding 2: py/clear-text-storage-sensitive-data (High) - gui.py:3280

**Root cause:** Config file written to disk in plain text via `tmp.write_text(new_text, "utf-8")`. Same as Finding 1.

**Fix applied:** Same as Finding 1 - moved sensitive config values to environment variable resolution.

## Finding 3: py/stack-trace-exposure (Medium) - webhook/server.py:163

**Root cause:** Exception details exposed in HTTP response body: `f"# Error generating metrics: {ex}\n"`. This leaks implementation details that could aid attackers.

**Fix applied:** Return generic error message instead of exception details; log details server-side only.
