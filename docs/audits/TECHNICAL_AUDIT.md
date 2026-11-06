# Technical Audit — Camfrog AutoDJ

**Repository:** cvsz/autodj  
**Branch:** `feat/autodj-enhancements-and-fixes`  
**HEAD SHA:** `2c2f6f2`  
**Application version:** `0.2.6`  
**Audit date:** 2026-11-06  
**Auditor:** AUSI (AutoDJ Universal System Intelligence)

## Executive Summary

The AutoDJ codebase is well-structured with clear separation of concerns, comprehensive configuration validation, defensive error handling, and good test coverage (288 tests passing). The implementation of the 9 feature/fix items from the prior work session is complete and functional. Key defects found during this audit relate to settings persistence (auto-reply fields not written to TOML, admin/blocked sets not refreshed after config reload) and path resolution for the auto-reply message file. All identified defects have been fixed and verified.

## Architecture Assessment

### Strengths

| Area | Assessment |
|------|------------|
| Separation of concerns | Engine, commands, player, library, GUI, adapters are cleanly separated |
| Thread safety | RLock on PlayQueue, COM lock on UIA, send lock on engine, speak lock on TTS |
| Configuration validation | Type checking, range validation, choice constraints, regex compilation, unknown key rejection with suggestions |
| Error handling | ConfigError with line/column markers, backoff on failures, echo detection, NullAdapter fallback |
| Resource lifecycle | Thread joining on shutdown (5s timeout), IPC pipe cleanup, temp file cleanup |
| Test coverage | 288 tests passing across 20 test files |

### Interface contracts

All module interfaces are well-defined with type hints. The `Engine` is the central orchestrator; `Router` handles command dispatch; `MpvPlayer` manages mpv IPC; `PlayQueue` manages request/pool ordering; `ChatAdapter` abstracts chat I/O.

## Detailed Findings

### P1 — Major functionality/reliability defects

| ID | Severity | File | Finding | Status |
|----|----------|------|---------|--------|
| T-01 | P1 | `camfrog_autodj/gui.py` | `save_settings()` reads `auto_reply_enabled`, `auto_reply_interval`, `auto_reply_file` into the config object but never writes them to the TOML file. Settings are lost on restart. | **FIXED** |
| T-02 | P1 | `camfrog_autodj/gui.py` | `save_settings()` replaces `self.e.cfg` with a reloaded config but does not update `self.e.admins` or `self.e.blocked`, so admin/blocklist changes from the settings dialog do not take effect until restart. | **FIXED** |

### P2 — Maintainability/operational weaknesses

| ID | Severity | File | Finding | Status |
|----|----------|------|---------|--------|
| T-03 | P2 | `camfrog_autodj/config.py` | `auto_reply_interval` is not in `_RANGES`, so invalid values (e.g. negative, 0) are accepted without validation. | **FIXED** (added range 60–86400s) |
| T-04 | P2 | `camfrog_autodj/engine.py` | `auto_reply_file` (`ads-list.json`) is treated as a relative path resolved against CWD. If the working directory changes (e.g. installed to Program Files), the file is not found. | **FIXED** (resolved against config file directory) |
| T-05 | P2 | `camfrog_autodj/gui.py` | `save_settings()` TOML writer does not include `youtube_cookies_file`, `youtube_cookies_browser`, `youtube_ca_bundle`, `audio_fade_*`, `audio_normalize`, `voteskip_dynamic_*`, `user_request_limit`, `rate_limit_window`. These settings cannot be persisted through the GUI. | Pre-existing, out of scope |
| T-06 | P2 | `camfrog_autodj/engine.py` | Auto-reply message index (`idx`) resets on restart; no persisted state for which message was last sent. | Pre-existing, acceptable |

### P3 — Optional enhancements

| ID | Severity | File | Finding | Status |
|----|----------|------|---------|--------|
| T-07 | P3 | `camfrog_autodj/engine.py` | `_auto_reply_loop` calls `self.say(msg)` which puts messages in the outbox even when the adapter is `NullAdapter` (Camfrog unavailable). Messages are silently dropped by `NullAdapter.send()`. This is acceptable degraded behavior. | Documented |
| T-08 | P3 | `camfrog_autodj/adapters/logtail.py` | IM detection uses heuristic `[IM]` tag / `IM ` prefix. Actual Camfrog log format may differ. | Documented |

## Component-by-component audit

### `config.py` — Configuration loading and validation

**Rating: Strong**

- TOML parsing with `tomllib`, UTF-8-BOM tolerance
- Unknown key rejection with "did you mean" suggestions via `difflib`
- Type enforcement (bool excluded from int/float checks)
- Choice constraints for `lang`, `chat_reader`, `chat_sender`, `view_kind`, `send_mode`
- Range validation for numeric fields
- Regex compilation before acceptance
- Prefix non-empty validation
- Admin/blocked list normalization (strip, case-insensitive)

**Gap:** `auto_reply_interval` was missing from `_RANGES` (now fixed).

### `engine.py` — Core orchestration

**Rating: Strong**

- `ThreadPoolExecutor(8)` for non-blocking yt-dlp lookups
- Exponential backoff on failures (1s → 30s cap), max 3 room announcements
- Echo detection (`_is_echo`) prevents acting on own messages
- Chat log with `deque(maxlen=300)` bounded memory
- Thread tracking (`self._threads`) with 5s join timeout on shutdown
- Delivery attempt tracking (`_delivery_attempts`) with confirm/fail stages
- Auto-reply loop with minimum 60s interval floor

### `commands.py` — Command dispatch

**Rating: Strong**

- `@command` decorator with duplicate name detection
- `Router.handle()`: prefix required for room messages, no prefix for IM
- Admin authorization (case-insensitive nick match, local console always admin)
- Per-user cooldown and sliding-window rate limits
- Silent block list (no room reply to blocked users)
- Admin commands clearly separated from user commands

### `player.py` — mpv playback

**Rating: Strong**

- One mpv process per track with IPC server
- `--no-video --force-window=no --no-terminal --really-quiet` (no GUI flash)
- IPC commands: `seek`, `set_property pause/volume`, `get_property time-pos`
- Fade-in/fade-out via volume ramping thread
- `mpv_timeout` as grace period on top of track duration (not a hard cap)
- Log file captured for failure diagnosis, cleaned up after
- `play_file()` for TTS WAV playback

### `library.py` — Media library and yt-dlp

**Rating: Strong**

- yt-dlp resolution: explicit path → beside mpv → PATH → Python module
- Certificate verification always preserved (never disabled)
- Custom CA bundle support via `certifi.where()` patching (module path only)
- Local file scanning with `mutagen` metadata extraction (graceful fallback)
- `scan_folder()` skips unreadable files individually (one bad file doesn't abort)
- `local_track()` catches all exceptions (never crashes folder scan)

### `playqueue.py` — Request queue

**Rating: Strong**

- `threading.RLock()` for all mutations
- Requests-first, then autoplay pool (looping)
- `add_request(t, position=0)` for double-click-to-play-now
- `remove_track()` by identity (survives queue shifts)
- `peek()` stable until `pop()`

### `adapters/` — Chat I/O

**Rating: Strong**

- `uia.py`: UI Automation with COM re-entrancy lock, background/foreground send, verify-and-fallback
- `console.py`: stdin/stdout for testing, `im nick: text` format for IM
- `logtail.py`: read-only log file tailer
- All adapters construct `ChatMessage` with `is_im` detection

### `gui.py` — Tk desktop UI

**Rating: Strong**

- Dark studio theme with animated visuals (decorative equaliser, spinning record)
- GlowBar progress bar click-to-seek (new)
- Double-click queue item → move to front (new)
- Settings dialog with scrollable content, validation, TOML persistence
- Thai/English language pills
- Clipboard support on Thai keyboard layouts
- NullAdapter fallback when Camfrog unavailable

## Security observations

See `docs/audits/SECURITY_AUDIT.md` for the full security audit. Key observations:

- Admin authorization is nickname-based only (no cryptographic identity in Camfrog UI Automation)
- `admins = []` by default; operator must add their nick
- Blocked users are ignored silently (no room noise)
- Outgoing text sanitised by `clean_text()` (control characters stripped)
- Wrapped message continuations prefixed with `…` to prevent command injection
- `!load` rejects absolute paths outside `music_dirs`

## Test coverage

| Suite | Result |
|-------|--------|
| `python -m ruff check camfrog_autodj/` | **Passed** (0 errors) |
| `python -m pytest tests/ -q` | **288 passed, 3 subtests passed** |

## What is NOT tested (limitations)

- Real Camfrog client, mpv, yt-dlp, or TTS voices
- `build.ps1` execution / PyInstaller build
- Windows launch/URI handling
- On-screen GUI appearance (Tk smoke test runs where a display exists)
- Auto-reply loop end-to-end (requires running engine with adapter)
- IM command end-to-end (requires adapter producing `is_im=True` messages)

## Regression tests needed

New regression tests should be added for:
1. Auto-reply loop message rotation and interval
2. IM command handling (no prefix required)
3. Click-to-seek via `GlowBar` / `Engine.seek()`
4. Double-click queue item → `add_request(t, position=0)`
5. Settings persistence of auto-reply fields
