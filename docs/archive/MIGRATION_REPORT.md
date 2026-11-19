# Migration Report — CamfrogAutoDJ v0.3.0

**Date:** 2026-11-16  
**Branch:** main (HEAD: fecc053)  
**Repository:** https://github.com/cvsz/autodj

---

## Executive Summary

No breaking migrations were required for this release. The codebase is backward-compatible with existing `config.toml` files. Configuration migration support exists in `autodj/migrate.py` for upgrading from older versions (placeholder detection and path discovery).

---

## Configuration Migration Support

The `autodj/migrate.py` module provides migration for existing installations:

| Feature | Description |
|---------|-------------|
| Placeholder detection | Detects installer placeholder values (e.g., `mpv_path = "REPLACE_ME"`) |
| Path discovery | Discovers valid executable paths for placeholders (mpv, yt-dlp) |
| Non-destructive | Placeholders that cannot be resolved are kept as-is; no config is overwritten without cause |
| Reporting | Lists all changes made and placeholders that couldn't be resolved |

**Entry point:** `migrate_config()` — called at startup via `__main__.py` ("Migrate placeholder/invalid values before loading config.")

---

## Changes Requiring No Migration

The following changes in v0.3.0 are backward-compatible and require no user action:

| Change | Compatibility |
|--------|---------------|
| `validate_installer.py` cross-platform skip | Internal tool only; no user config impact |
| `.gitignore` / `.dockerignore` updates | Local git/docker config only; no user config impact |
| `docs/optimize.md` secret sanitization | Documentation only; no code or config impact |
| `CHANGELOG.md` update | Documentation only |

---

## Configuration Schema Stability

The `Config` dataclass in `autodj/config.py` is stable. All fields have sensible defaults. New fields added in v0.3.0 include:

- `webhook_cors_origins` (default: `["*"]`)
- All RE integration toggles (default: `true`)
- IM viewer/auto-reply settings
- Admin command config gates

Existing `config.toml` files continue to work without modification. Unknown keys are rejected with "did you mean" suggestions, but existing valid keys are unaffected.

---

## Migration Testing

| Test | Result |
|------|--------|
| `test_migrate_mpv_path_placeholder` | PASS |
| `test_migrate_ytdlp_path_placeholder` | PASS |
| `test_placeholder_kept_when_no_valid_path` | PASS |
| `test_detect_placeholders_various_forms` | PASS |
| `test_detect_empty_string_is_placeholder` | PASS |
| `test_detect_no_placeholder_for_valid_path` | PASS |
| `test_config_without_placeholders_no_migration` | PASS |

All 9 migration tests pass.

---

## Recommendations

1. **No user migration required.** Existing installations can upgrade to v0.3.0 without config changes.
2. **Placeholder detection runs at startup.** Installer placeholders are automatically detected and reported; unresolvable placeholders are preserved.
3. **Backup before upgrade.** As always, users should back up `config.toml` and `playlist.json` before upgrading (atomic writes with `.bak` backup are already implemented).

