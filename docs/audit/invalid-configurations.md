# Invalid Configurations — Camfrog AutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`  
**Status:** Config validation reviewed; no invalid configuration accepted silently

## Validation (`config.py`)

`Config.load()` rejects:
- Unknown settings (with "did you mean" hint via `difflib`).
- Wrong types for a setting (text/whole number/number/true-false/list).
- Non-string items in list settings.
- Values outside `_RANGES` (volume 0-100, max_queue 1-100000, max_duration 1-604800, cooldown, send_interval, max_msg_len 20-2000, poll_interval, tts_duck, search_limit, mpv_timeout, fade times, voteskip_dynamic_pct, user_request_limit, rate_limit_window, auto_reply_interval, im_auto_reply_cooldown).
- Values not in `_CHOICES` (lang, chat_reader, chat_sender, view_kind, send_mode).
- Invalid regexes for `window_title_re`, `process_re`, `window_exclude_re`, `line_regex`, `client_title_re`.
- Empty `prefix`.
- Non-existent config file is not an error — runs with built-in defaults and a warning.

## Migration (`migrate.py`)

Placeholder values (`REPLACE_ME`, `CHANGE_ME`, `TODO`, `FIXME`, `XXX`, empty paths) in `mpv_path`/`ytdlp_path` are detected; valid paths are discovered (registry, relative to config/app dir, common Windows locations) and written atomically with backup. Valid custom operator values are never replaced.

## No silently-accepted invalid values

All invalid configuration raises explicit `ConfigError` with a message written for the person editing the file (TOML syntax errors include the offending line and a `^` marker). No setting is silently replaced with a default.
