# Invalid Configurations — cvsz/autodj

`config.py` validates every setting with explicit errors (fail-closed, never silent replacement):

- Unknown keys → `ConfigError` with "did you mean" hint (difflib).
- Wrong types → `ConfigError` describing expected type.
- Out-of-range values → `ConfigError` with bounds.
- Invalid regexes (`window_title_re`, `process_re`, `line_regex`, etc.) → `ConfigError`.
- Empty `prefix` → `ConfigError`.
- `admins`/`blocked_users` stripped and validated.
- Choices enforced: `lang`, `chat_reader`, `chat_sender`, `view_kind`, `send_mode`.

The GUI settings dialog (`gui.py save_settings`) now validates the assembled candidate TOML with `Config._validate` (ranges, choices, regexes) **before** any write; invalid values raise `ValueError` and nothing is written. Backup (`.bak`) + atomic write (`.tmp` + `os.replace`) used on every write.

Search of git history for accidentally committed secrets: **none found** (`git grep` for `ghp_`, `github_pat_`, `AKIA`, `BEGIN ... KEY`, `ssh-rsa` → 0 matches; `git ls-files` for `.env`/`id_rsa`/`.pem`/`.key` → 0 tracked secret files, excluding `.env.example`).

No invalid configuration values exist in tracked config files (`config.default.toml`, `config.example.toml`, `config.toml`, `config.toml.bak` all parse with `tomllib`). No placeholder `REPLACE_ME` values are left in tracked configs (the commented `camfrog_exe = "REPLACE_ME:..."` in `config.default.toml` is intentionally commented documentation).

## Conclusion

No invalid configurations detected. Config validation is explicit, fail-closed, and tested (`tests/test_core.py`, `tests/test_hardening.py`, `tests/test_migration.py`).
