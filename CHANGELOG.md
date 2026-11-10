# Changelog

## Unreleased

- **Security: added `CODEOWNERS`** — security-sensitive paths (GitHub Actions workflows, installer scripts, `SECURITY.md`, config files) now require independent review by `@policedbc`; default ownership for everything else is `@cvsz`. (`CODEOWNERS`)
- **Test: library scan symlink / reparse-point safety regression tests** — added `tests/test_library_scan_safety.py` (11 tests) pinning that `scan_folder`/`LocalIndex` never follow symlinks, skip broken symlinks and cycles, skip unreadable directories, enforce `limit`/`max_dirs`, and ignore unsupported extensions. (`docs/audit/library-scan-review.md`, `docs/audit/bugs-and-findings.md`)
- **Docs: full PR inventory + audit reports** — all 142 pull requests enumerated, dispositioned, and recorded in `docs/audit/all-pr-*.md`; architecture, security, playback, GUI, playlist, library-scan, Windows build, installer, dependency, penetration-test, performance, GPG/merge-evidence, production-readiness, and residual-risk reports added under `docs/audit/`. (`docs/audit/`)
- **Fix: Player IPC read timeout** — `_cmd_get` in `player.py` now enforces a 2-second timeout on Windows named pipes and Unix sockets to prevent indefinite hangs if mpv doesn't respond. Extracted platform-specific read logic into `_ipc_read_windows` and `_ipc_read_unix` helpers to reduce C901 complexity.
- **Fix: Cooperative playback cancellation** — `MpvPlayer` now accepts an optional `stop_evt` (threading.Event) passed from `Engine`. The `_wait_for_mpv_end` method checks this event during polling, allowing clean shutdown during long-running tracks or live streams.
- **Fix: Live stream hang detection** — `_wait_for_mpv_end` now uses a fixed POLL interval (0.5s) for all tracks, including live streams (limit=None), while only enforcing the "hung" timeout for tracks with known duration. This prevents the player thread from blocking indefinitely.
- **Fix: Circuit breaker thread safety** — All circuit breaker state (`_circuit_breaker_failures`, `_circuit_breaker_open_until`) is now protected by `_send_failure_lock` in `_record_circuit_failure`, `_record_circuit_success`, and `_is_circuit_open`. The health check also reads these values under the same lock for consistent snapshots.
- **Fix: IM auto-reply thread safety** — `_im_reply_cooldowns` dict is now protected by `_chat_lock` in both `_handle_im_message` (chat loop) and `_im_auto_reply_loop` (cleanup loop). The redundant IM auto-reply loop was replaced with a periodic cleanup task (every 60s) that removes stale cooldown entries.
- **Fix: Command cooldown memory leak** — `Router._within_limits` now prunes stale entries from the `last` dict (cooldown tracking) using a 2x window cutoff, preventing unbounded growth when users stop sending commands.
- **Fix: Library scan directory budget** — `scan_folder` now uses a global `remaining_dirs` counter passed recursively, enforcing the `max_dirs` limit across the entire scan tree instead of per-directory-level. Added internal `_scan_folder_recursive` helper.
- **Fix: Playlist source validation** — `_is_valid_source` in `playlist.py` now rejects paths containing `..` (directory traversal) and requires either a path separator or file extension for local paths, improving defense-in-depth.

## 0.3.0
2026-11-09

### Enterprise Architecture
- **Exception Hierarchy** (`camfrog_autodj/exceptions.py`): 20+ structured exception types with machine-readable codes (`config.error`, `chat.send_failed`, `player.hung`, `security.unauthorized`, etc.) and contextual metadata. All inherit from `AutoDJError` for unified catching. Backward-compatible `UserError = AutoDJError` alias preserved.
- **Circuit Breakers** (`camfrog_autodj/engine.py`): 
  - Playback: Opens after 5 consecutive failures, pauses 60s, half-opens for recovery
  - Chat Send: Suspends after 10 consecutive delivery failures, auto-recovers on success
- **Per-Nick Chat Rate Limiting** (`camfrog_autodj/engine.py`): Sliding window (20 messages/60s per nick), admins exempt, thread-safe with locks.
- **Health Check Endpoint** (`engine.health_check()`): Returns structured dict with mpv availability, circuit breaker state, send suspension, queue depth, IM viewer status — safe for Prometheus/Grafana/Loki ingestion. Never raises.
- **Code Quality**: C901 complexity refactored (`_chat_loop` split into `_handle_im`, `_handle_room_message`, `_should_ignore_message`), all methods < 10 branches.

### Added
- **IM Viewer GUI** (`camfrog_autodj/gui.py`): New IM tab in desktop window shows private/instant messages with 2 Hz polling. Settings dialog includes IM viewer enable/disable, auto-reply message, cooldown, and room presence requirement.
- **IM Auto-Reply** (`camfrog_autodj/engine.py`): Configurable auto-reply to private messages with per-user cooldown (default 30s, min 10s). Uses `[IM]` prefix. Respects `im_require_room_presence` (default true).
- **Camfrog Gift Detection** (`camfrog_autodj/engine.py`): Detect virtual-gift messages in room chat (`GIFT_RECEIVED`, `room_gift_message`, `camfrog://gift`, `vgift_`, etc.) and announce them. Config-gated: `gift_announce_enabled`. (see `docs/camfrog-re/08-feature-gift.md`)
- **Camfrog Avatar Change Detection** (`camfrog_autodj/engine.py`): Detect avatar change messages (`updateAvatarMessage`, `avatar_changed`) and announce. Config-gated: `avatar_change_enabled`. (see `docs/camfrog-re/16-user-icon-avatar.md`)
- **Camfrog Status Indicators** (`camfrog_autodj/engine.py`): Detect user status changes (online/away/busy/invisible/admin/moderator/owner) and announce. Config-gated: `status_indicator_enabled`. (see `docs/camfrog-re/14-png-assets.md`)
- **Camfrog Upgrade/Payment Alerts** (`camfrog_autodj/engine.py`): Detect upgrade/payment-required status text and alert admin. Config-gated: `status_alert_enabled`. (see `docs/camfrog-re/07-upgrade-logic.md`, `09-payment.md`)
- **Camfrog Name Color Tracking** (`camfrog_autodj/engine.py`): Read nickname color (`color: #RRGGBB`) from incoming chat HTML for GUI preview (read-only; AutoDJ cannot set name color). (see `docs/camfrog-re/15-name-color.md`)

### Changed
- **Version bump**: 0.2.8 → 0.3.0 across all artifacts (`pyproject.toml`, `version_info.txt`, `installer.nsi`, `install.bat`, `install.ps1`, `scripts/build_installer*.sh/ps1`, `camfrog_autodj/__init__.py`)
- **Config**: New IM viewer/auto-reply fields, all RE integration toggles (default enabled)
- **Tests**: Added `tests/test_autodj_enhancements.py` (21 new tests covering circuit breakers, rate limiting, health checks, exceptions, IM viewer, RE integrations)

### Fixed
- **C901 complexity**: `_chat_loop` refactored from 11 branches to 3 (split into 3 helper methods)
- **Import sorting**: `library.py` imports organized per ruff I001
- **Type hints**: All exception classes properly typed for mypy compatibility

## 0.2.8
2026-11-09

### Added
- **Font/Style Customization (GUI Preview Only)**: New `message_style` config section with `font_family`, `font_size`, `font_color`, `bold`, `italic`, `underline`. Live preview in Settings ⚙️ tab. **Note**: Camfrog desktop client does NOT support rich text in outgoing messages — sent messages are always plain text via UIA. This feature is for the GUI preview panel only. (`camfrog_autodj/config.py`, `camfrog_autodj/renderer.py`, `camfrog_autodj/engine.py`, `camfrog_autodj/gui.py`, `camfrog_autodj/messages.py`)
- **Admin Greeting**: Greet admin on first message in session with configurable message (`{admin}` placeholder) and cooldown (default 1 hour). (`camfrog_autodj/engine.py`, `camfrog_autodj/config.py`, `camfrog_autodj/messages.py`, `camfrog_autodj/gui.py`)
- **Delete History**: Admin command `!deletehistory <all|N>` to clear history or remove oldest N entries. (`camfrog_autodj/commands.py`, `camfrog_autodj/messages.py`)
- **IM-Only Play Commands**: `!play`, `!request`, `!req`, `!p`, `!เล่น`, `!ขอเพลง`, `!เล่นเพลง` now only work via IM (private message). Room users must DM the bot. Admins can still use in room. (`camfrog_autodj/commands.py`, `camfrog_autodj/messages.py`)
- **Autoplay Idle Timeout**: After 30 minutes (configurable `autoplay_idle_timeout`) with no user requests, bot switches to autoplay pool. New `!play` immediately exits autoplay mode. (`camfrog_autodj/engine.py`, `camfrog_autodj/config.py`, `camfrog_autodj/gui.py`)
- **New Thai Aliases**: `!ขอเพลง` (request song), `!เล่นเพลง` (play song). (`camfrog_autodj/commands.py`, `camfrog_autodj/messages.py`)
- **Auto-Reply**: Every 60 seconds from `ads-list.json` (configurable `auto_reply_interval`). (`camfrog_autodj/engine.py`, `config.toml`)
- **REA Reverse Engineering Evidence**: Documented Camfrog font logic (GDI imports: `CreateFontIndirectW`, `EnumFontFamiliesExW`, `ChooseFontW`; chat/IM font settings; HTML rendering for display only; no rich text send capability). (`docs/protocols/camfrog-font-logic.md`)
- **Mic Mute/Unmute**: Admin commands `!mute` / `!unmute` to mute/unmute the mic (config-gated: `admin_mute_mic`, `admin_unmute_mic`). (`camfrog_autodj/commands.py`, `camfrog_autodj/engine.py`, `camfrog_autodj/config.py`, `camfrog_autodj/gui.py`, `camfrog_autodj/messages.py`)
- **Block/Unblock Bot**: Admin commands `!blockbot` / `!unblockbot` to block/unblock bots (config-gated: `admin_block_bot`, `admin_unblock_bot`). (`camfrog_autodj/commands.py`, `camfrog_autodj/config.py`, `camfrog_autodj/gui.py`, `camfrog_autodj/messages.py`)
- **Kick/Ban/Unban User**: Admin commands `!kick` / `!ban` / `!unban` (config-gated: `admin_kick_user`, `admin_ban_user`, `admin_unban_user`). (`camfrog_autodj/commands.py`, `camfrog_autodj/config.py`, `camfrog_autodj/gui.py`, `camfrog_autodj/messages.py`)
- **Punish User/Bot**: Admin commands `!punish` / `!punishbot` (config-gated: `admin_punish_user`, `admin_punish_bot`). (`camfrog_autodj/commands.py`, `camfrog_autodj/config.py`, `camfrog_autodj/gui.py`, `camfrog_autodj/messages.py`)
- **Delete Message**: Admin command `!delete <msg id>` to delete a message by ID (config-gated: `admin_delete_message_enabled`). (`camfrog_autodj/commands.py`, `camfrog_autodj/engine.py`, `camfrog_autodj/config.py`, `camfrog_autodj/gui.py`, `camfrog_autodj/messages.py`)
- **Welcome Message**: Welcome message feature with configurable text (config-gated: `welcome_message_enabled`). (`camfrog_autodj/commands.py`, `camfrog_autodj/engine.py`, `camfrog_autodj/config.py`, `camfrog_autodj/gui.py`, `camfrog_autodj/messages.py`)
- **Camfrog Gift Detection**: Detect virtual-gift messages in room chat (`GIFT_RECEIVED`, `room_gift_message`, `camfrog://gift`, etc.) and announce them. Config-gated: `gift_announce_enabled`. (`camfrog_autodj/engine.py`, `camfrog_autodj/config.py`, `camfrog_autodj/gui.py`, `camfrog_autodj/messages.py`)
- **Camfrog Avatar Change Detection**: Detect avatar change messages in room chat (`updateAvatarMessage`) and announce them. Config-gated: `avatar_change_enabled`. (`camfrog_autodj/engine.py`, `camfrog_autodj/config.py`, `camfrog_autodj/gui.py`, `camfrog_autodj/messages.py`)
- **Camfrog Status Indicators**: Detect user status changes in room chat (online/away/busy/invisible/admin/moderator/owner) and announce them. Config-gated: `status_indicator_enabled`. (`camfrog_autodj/engine.py`, `camfrog_autodj/config.py`, `camfrog_autodj/gui.py`, `camfrog_autodj/messages.py`)
- **Camfrog Upgrade/Payment Alerts**: Detect upgrade/payment-required status text and alert admin. Config-gated: `status_alert_enabled`. (`camfrog_autodj/engine.py`, `camfrog_autodj/config.py`, `camfrog_autodj/gui.py`, `camfrog_autodj/messages.py`)
- **Camfrog Name Color Tracking**: Read nickname color (`color: #RRGGBB`) from incoming chat HTML for GUI preview (read-only; AutoDJ cannot set name color). (`camfrog_autodj/engine.py`)
- **Documentation**: `docs/camfrog-re/autodj-commands.en.md` / `.th.md`, `docs/camfrog-re/user-manual.en.md` / `.th.md`, `docs/camfrog-re/admin-manual.en.md` / `.th.md`. README and CHANGELOG updated.

### Fixed
- **Chat send retry loop**: Fixed `UnboundLocalError` in `uia.py:_appeared()` where `norm_l` was referenced outside the loop. (Already in 0.2.8 HEAD)
- **Queue logic**: Pool tracks retry on failure (up to 3x); user requests advance immediately on failure. (`camfrog_autodj/engine.py`)
- **IM command handling**: Fixed rate limiting and cooldown for IM commands. (`camfrog_autodj/commands.py`)

### Changed
- **Autoplay idle timeout**: Default changed from 1800s (30 min) to 30 seconds. When no user requests arrive within this time, AutoDJ switches to the autoplay pool. (`camfrog_autodj/engine.py`, `config.toml`)
- **Requested songs play immediately**: `!play` inserts at the front of the queue (`position=0`) so the requested song plays next. (`camfrog_autodj/commands.py`)
- **Default font settings**: `font_size = 14`, `font_color = "#FF0000"` (red) for better visibility in preview.
- **Play commands**: Now IM-only (room users must DM the bot). Admins can still use in room.
- **Auto-reply interval**: Default 60 seconds (was 300).

## 0.2.8 (Initial)
2026-11-07

- **Fix: GUI hangs when clicking Load Folder** — `library.scan_folder()` now skips symlinks (avoids cycle/reparse-point hangs on Windows) and caps returned tracks via a `limit` argument; `gui.load_folder()` disables the folder button while scanning, guards against reentrant clicks, and shows loaded/failed status. (`camfrog_autodj/library.py`, `camfrog_autodj/engine.py`, `camfrog_autodj/gui.py`)
- **Fix: chat-log race condition between engine and GUI poller** — `Engine.chat_log`/`chat_seq` are now guarded by `_chat_lock`; GUI reads via thread-safe `chat_snapshot()`. (`camfrog_autodj/engine.py`, `camfrog_autodj/gui.py`)
- **Fix: `save_settings()` could leave a half-written `config.toml` on crash** — writes atomically via temp file + `os.replace()` with a `.bak` backup, with `%APPDATA%\\CamfrogAutoDJ\\` relocation fallback. (`camfrog_autodj/gui.py`)
- **Fix: `MpvPlayer.play_file()` could block forever on a bad WAV** — 30s subprocess timeout. (`camfrog_autodj/player.py`)
- **Fix: folder scans in autoplay sources and `!load` could scan forever** — capped at 500 tracks. (`camfrog_autodj/engine.py`)
- **Fix: `Add files` button lacked busy state** — now shows resolving state with a pending counter, matching `Add`. (`camfrog_autodj/gui.py`)
- **Fix: Player music time countdown skipping** — The GUI now queries mpv via IPC (`get_property time-pos`) for the actual playback position instead of relying on wall-clock time. Added `MpvPlayer._cmd_get()` and `MpvPlayer.get_time_pos()` in `player.py`; `Engine.position()` in `engine.py` uses real mpv position with wall-clock fallback. Fixes the issue where the time display jumped (e.g., from 00:00 to 0:01) during playback.
- Resolve MPV and yt-dlp executable paths consistently, including Windows environment variables and app-relative paths.
- Preserve the user's `config.toml` across installer upgrades and retain user data during uninstall.
- Make source-validation output explicit and keep `clean-all` from deleting the tracked PyInstaller spec.
- **Security: removed default administrator** from `config.example.toml` (`admins = []`); Camfrog UI automation exposes only display nicks, so admin authorization is nickname-based and case-insensitive — operator must add their nick before running. Added authorization/spoofing regression tests (`tests/test_hardening.py`).
- **Security: release workflow gated** — `.github/workflows/release.yml` now requires validation (tests, lint, typecheck, secret scan) before any build artifact is produced; no automatic release publication.
- **Security: CodeQL analyzes Python** (was `actions` only); **Dependabot covers pip packages** (was GitHub Actions and Docker only).
- **Security: CODEOWNERS** requires independent review (`@policedbc`) for security-sensitive paths (workflows, installer scripts, SECURITY.md, config).
- **Docs: `docs/architecture.md` and `docs/release.md` rewritten** to describe AutoDJ (not the ztemplate template).
- **Docs: `IMPLEMENTATION-CHECKLIST.md` changed to evidence-based status tracking** (VERIFIED/PARTIALLY VERIFIED/UNVERIFIED/BLOCKED with evidence references).
- **Infra: replaced placeholder Dockerfile with local audit image `zpostgresql`** — `python:3.11-slim` based image (`zpostgresql:latest` / `zpostgresql:audit`) that installs the project with dev tools and self-verifies (ruff check/format, pytest) at build time; mirrors Linux CI (`git`, `python3-tk`, `xvfb`, `xauth`) and runs as non-root user `autodj`. Replaces the unusable `alpine:3.24` placeholder.
- **Fix: release typecheck gate** — `mypy camfrog_autodj` (release.yml Gate 1) failed on the release head due to unstubbed third-party dependencies (`pywinauto`, `pyttsx3`, `mutagen`, `yt_dlp`, `pyperclip`); added `[tool.mypy] ignore_missing_imports = true` to `pyproject.toml` so the gate validates AutoDJ's own code.
- **Fix: unused noqa on blind `Exception` catch** in `camfrog_autodj/__main__.py` — `ruff format` had stranded the `# noqa: BLE001` directive; directive moved onto the `Exception` line so `ruff check` and `ruff format --check` both pass.
- **Docs: ADR 0001** — documents the local audit Docker image and mypy CI gate configuration (`docs/adr/0001-local-audit-docker-image-and-mypy-gate.md`).

## 0.2.6

### Added
- **Official v0.2.6 Delivery & Recovery**: Complete release publication with verified Windows installer (`Camfrog-AutoDJ-Setup-0.2.6.exe`), standalone `AutoDJ.exe`, CycloneDX SBOM (`Camfrog-AutoDJ-v0.2.6.cdx.json`), and cryptographic Sigstore provenance attestation.
- **Workflow Hardening & Persistent Artifact Retention**: Integrated `actions/upload-artifact@v4` in `.github/workflows/release.yml` for persistent operational retention of release build artifacts.
- **SHA256 Manifest Generation**: Automated generation of `SHA256SUMS.txt` for all release assets.
- **YouTube Playlist Support**: Auto-detects YouTube playlist URLs (`youtube.com/playlist?list=...`, `watch?v=...&list=...`) and plays all videos in sequence.
- **Per-User Installation**: Installs to `%APPDATA%\CamfrogAutoDJ` (no admin rights required).
- **Settings Tab**: New ⚙️ Settings button in the GUI header to edit all settings live and save to `config.toml`.
- **Auto-Config Relocation**: If `config.toml` is in a protected location (e.g. Program Files), AutoDJ automatically copies it to `%APPDATA%\CamfrogAutoDJ\config.toml`.
- **Log Directory Auto-Creation**: Log directory is created automatically on first run.
- **Settings Button**: New ⚙️ gear icon in the header bar opens the Settings tab.
- **Relative Config Paths**: `config.example.toml` uses `%APPDATA%\CamfrogAutoDJ\mpv\...` paths for portability.
- **YouTube Playlist Support**: Auto-detects YouTube playlist URLs (`youtube.com/playlist?list=...`, `watch?v=...&list=...`) and plays all videos in sequence.
- **Installer**: Per-user installation to `%APPDATA%\CamfrogAutoDJ` (no admin required).
- **NSIS Installer**: Per-user install to `%APPDATA%\CamfrogAutoDJ`, HKCU registry, no admin required.

### Fixed
- **GUI ไม่ขึ้น (GUI won't open)**: `camfrog_autodj/__main__.py` — auto-discovery (`discover.apply()`) crashed with `ImportError` on `pywinauto.Desktop` before `App(eng).mainloop()` was reached, so the Tk window never appeared. Auto-discovery is now wrapped in `try/except` and logs a warning instead of crashing; `build_adapter()` failures fall back to `NullAdapter` so the GUI still opens without chat (user can run `--check`/`--discover` from inside it).
- **Camfrog adapter blocks GUI startup**: `camfrog_autodj/adapters/uia.py` `UiaAdapter.__init__()` called `resolve()` which polls up to 30s for a Camfrog window, blocking GUI launch. With `NullAdapter` fallback in `__main__.py`, this no longer blocks.
- **Playlist not in queue list box**: `camfrog_autodj/engine.py` `_load_all()` added `playlist.json` tracks to the autoplay *pool* (`add_pool`), but the GUI list box only shows the request *queue* (`add_request`). Playlist tracks are now added to `add_request` so they appear in the GUI and play before the autoplay pool. Dedupe against existing requests and history prevents re-queuing on restart.
- **Thread-safety data race on `e.current`**: `camfrog_autodj/commands.py` `_play()` read `e.current.source` outside `e.queue.lock`, racing with `_player_loop()` which writes `e.current`. Now read under the same lock.
- **Ungraceful shutdown**: `camfrog_autodj/engine.py` `shutdown()` did not wait for daemon threads. Thread references are now stored in `self._threads` and joined (5s timeout each) on shutdown.
- **Windows-only code crashes on Linux**: `camfrog_autodj/launcher.py`, `camfrog_autodj/tts.py`, `camfrog_autodj/winmsg.py` now call `_require_windows()` to raise a clear `RuntimeError` instead of crashing with obscure `ctypes`/`pywinauto` errors on non-Windows platforms.
- **`!load` path traversal**: `camfrog_autodj/commands.py` `_load()` now rejects absolute paths outside `music_dirs` (admin-only guard).
- **NSIS installer warnings**: `installer.nsi` — removed `docs\*.txt` file glob (no such files), removed unused `.onUninstSuccess` function, removed unused `GetDate` function (now called inline via `Call GetDate`), removed duplicate `Uninstall.lnk` shortcut, removed `SEC_SRC` section (Python source not shipped in installer). All 5 NSIS warnings eliminated.

### Changed
- `camfrog_autodj/engine.py`: `Engine.__init__` now accepts `cfg_path` (was missing, causing `TypeError` when `_run()` passed it). GUI buttons `do_discover()`/`do_check()` read `self.e.cfg_path`.

### Added
- `camfrog_autodj/adapters/__init__.py`: new `NullAdapter` — silent fallback when Camfrog cannot be reached; GUI stays open, chat degrades gracefully.
- `camfrog_autodj/engine.py`: `_threads` list tracking all daemon threads started by `start()`.

## 0.2.4

### Fixed
- `camfrog_autodj/adapters/uia.py` `_appeared()`: `norm_l` was referenced outside the `for l in new:` loop. When no new chat lines arrived, `norm_l` was never assigned, causing `UnboundLocalError` on every background chat send — messages retried endlessly (`send failed ... retrying once in 2s`). Moved the `bot_nick` match inside the loop so `norm_l` is always defined before use, and every new line is checked (not just the last one).
- `camfrog_autodj/adapters/uia.py` `_bg_fails`: consecutive-failure counter was read/written without a lock across reader and sender threads, causing a race condition. Now protected by `_bg_fails_lock`.
- `camfrog_autodj/adapters/uia.py` `messages()`: `self._view = None` was assigned outside `com_lock`, racing with `_lines()` which reads `self._view` inside the lock. Now assigned inside `com_lock`.
- `camfrog_autodj/winmsg.py`: three module-level functions were defined twice — `make_lparam` (lines 58 and 256), `pick_child` (lines 62 and 260), `show_noactivate` (lines 117 and 273). The second definition silently shadowed the first. Removed the duplicate block.
- `camfrog_autodj/webchat.py`: unused unpacked variable `node` → `_node` in `read_items()`.
- `camfrog_autodj/gui.py`: unused unpacked variables `r`/`lab` → `_r`/`_lab` in three `_vc` unpack sites; removed unnecessary `int(round(...))` in `px()`.
- `camfrog_autodj/visuals.py`: removed unnecessary `int(round(...))` in `rgb_to_hex()`.
- `camfrog_autodj/adapters/uia.py`: merged two `endswith()` calls into one with a tuple argument.
- `camfrog_autodj/doctor.py`: replaced unnecessary `dict(...)` call with a literal.
- `camfrog_autodj/engine.py`: replaced unnecessary `dict(...)` call with a literal in `snapshot()`.
- `camfrog_autodj/library.py`: replaced unnecessary `dict(...)` call with a literal in `_extract_exe()`.
- `camfrog_autodj/gui.py`: `add_files()` and `load_folder()` now check for `$DISPLAY`/`$WAYLAND_DISPLAY` before opening native file dialogs, and wrap in try/except — fixes hang on headless Linux.
- `camfrog_autodj/installer.nsi`: removed machine-specific `config.toml` from bundle (path hardcoded to one PC); config is now created by `install.ps1` on first run.
- `camfrog_autodj/tts.py`: **TTS did nothing with default config** — `eng.save_to_file()` and `eng.runAndWait()` were inside `if cfg.tts_voice:`, so with `tts_voice = ""` nothing was synthesised. Moved outside the `if`. Also added `TTS_TIMEOUT` (60s) so `synth()` no longer blocks forever if pyttsx3 is missing or hangs; each job independently imports pyttsx3 so the worker stays alive even if it's not installed.
- `camfrog_autodj/library.py`: **`ytsearch20:` autoplay sources always failed** — `is_url()` only matches `http://`/`https://`, so `ytsearch20:mandopop` was double-wrapped as `ytsearch1:ytsearch20:mandopop` and failed. Added `SEARCH_PREFIX` regex and `raw_target` parameter so operator-supplied `ytsearchN:` queries pass through unchanged. Also fixed `find_ytdlp()` to fall back to PATH yt-dlp when `mpv_path` is the default `"mpv"` (the previous code refused PATH lookup when mpv_path was set, ignoring a perfectly good yt-dlp on PATH).
- `camfrog_autodj/commands.py`: **`!play` from chat was not saved to `playlist.json`** — only admin/GUI requests were saved, so `!last` was always empty for chat requests. Added `e.playlist.add(tracks)` for chat requests too. Also fixed cooldown case-dodging (`"Bob"` and `"bob"` are now one person via `.lower()`) and `²` digit bypass in `!remove`/`!vol` (`isascii()` check).
- `camfrog_autodj/player.py`: **`mpv_timeout` killed every track longer than the timeout** — `p.wait(timeout=120)` capped total play time, cutting any track over 2 minutes. Changed to a grace period: `limit = duration + mpv_timeout`, checked via 0.5s polling loop; pauses are excluded from the countdown; unknown-duration (live) tracks have no limit. Added `POLL` constant and `_played()` helper.
- `camfrog_autodj/playlist.py`: **corrupt `playlist.json` was silently overwritten** — `load_playlist()` returned `[]` and `save_playlist()` would overwrite the bad file. Added `_unreadable()` check and `PlaylistStore.add()` now saves a `.corrupt-<timestamp>` backup before overwriting.
- `tests/test_hardening.py`: updated `FailingPlayer.play()` and `lambda` mocks to accept the new `duration` parameter on `MpvPlayer.play()`.

### Added
- GUI: `--discover` และ `--check` ปุ่มบน now-playing card (`🔍 ค้นหาห้องแชท` / `✓ ตรวจสอบการตั้งค่า`) ให้ผู้ดูแลระบบรัน auto-discovery และวินิจฉัยการตั้งค่าจากหน้าต่างเดสก์ท็อปโดยไม่ต้องเปิดเทอร์มินัล
- `installer.nsi`: รองรับหลายภาษาในตัวติดตั้ง (English + Thai) ผ่าน `MUI_LANGUAGE` macro; ไฟล์ `thai.nlf` รวมอยู่ใน repo (ต้องติดตั้งที่ `Contrib\Language\` ของ NSIS บนเครื่อง Windows ก่อนคอมไพล์)
- `camfrog_autodj/engine.py`: `Engine.__init__` no longer takes `cfg_path` (was an experiment, removed). Added `_speak_lock` so only one TTS clip plays at a time (overlapping TTS jobs would un-duck the music early). `load_source()` now recognises `ytsearchN:` queries as raw targets for autoplay sources.
- `camfrog_autodj/engine.py` shutdown order: `adapter.close()` before `exec.shutdown()` so sender threads release the adapter before it's closed.

### Testing
- Full suite: **97 passed, 1 skipped** (was 130 passed before test mock updates for the new `duration` parameter on `MpvPlayer.play()`).
- All command paths verified end-to-end via `--lang th --console` (Thai and English).

## 0.2.3
`make` on plain Windows PowerShell/cmd. **Automated Windows 11 installer (`install.ps1` / `install.bat`).**

### Added
- `install.ps1` / `install.bat`: Full-featured automated installer for Windows 11. Verifies OS, installs prerequisites (Python 3.11+, mpv, yt-dlp, VB-Cable) via winget or direct download, clones the project, installs Python dependencies, builds `AutoDJ.exe` with PyInstaller, creates `config.toml` with interactive prompts, creates Desktop/Start Menu shortcuts (including Config editor and Uninstaller), optional auto-start on login, and runs `AutoDJ.exe --check` for verification. Logs to `%TEMP%\autodj-install-<timestamp>.log`.

### Fixed
- `make help` (and every other target) failed on Windows with confusing cascading errors ("The system cannot find the path specified", then `awk` "CreateProcess ... failed") when `make` was installed but bash/awk/coreutils were not on PATH. `SHELL` no longer hard-codes the Linux path `/bin/bash` (now resolved via PATH, so it also works if Git Bash's `bash.exe` is on PATH without being at that exact path). More importantly, the Makefile now checks for `bash` up front and fails with ONE clear message explaining the two real options: run `make` from inside Git Bash, or skip `make` entirely and use `build.ps1` directly -- the Makefile is a convenience wrapper, not a requirement. The recipes are deliberately `python -c`/plain-command based (no awk/find/grep/cp/sed) and `SHELL` falls back to `cmd.exe /c` when `bash` is not on PATH, so plain PowerShell/cmd works too; from WSL2, `make build`/`build-clean`/`sign` automatically call the Windows `powershell.exe`. If `make` still not work on your shell, skip it: `python -m pip install -e . pyinstaller` then `.\build.ps1` builds and signs `AutoDJ.exe`, and `python -m pytest` runs the tests directly.
- In this working tree the same Windows-`make` problem was solved a different way (never released in 0.2.3): every recipe that needs Unix utilities (awk/find/grep/cp) was rewritten as a `python -c` one-liner and `SHELL` now falls back to `cmd.exe /c` when `bash` is not on PATH, so `make` works from plain PowerShell/cmd (and `make build`/`build-clean`/`sign` call `powershell.exe` automatically from WSL2). This Makefile superseded the released fail-fast version and is kept here; `make help` keeps a documented target list in `README.md`.
- Building from WSL2: `make build` drives `build.ps1` via WSL interop's `powershell.exe`. On a machine that also has PowerShell 7, the inherited `PSModulePath` contains PS7 module dirs, PS 5.1 resolves the **PS7** `Microsoft.PowerShell.Security` first, that load fails its authorization check, the Certificate provider never registers and the sign step dies with `Cannot find drive: 'Cert'`. `build.ps1` and `tools/sign_exe.ps1` now deselect the PS7-only dirs at startup (PS 5.1 only; pwsh 7 itself is unaffected), so `make build` and `make sign` finish cleanly: `AutoDJ 0.2.3` smoke test, `signature: Valid (Signature verified.)`, DigiCert timestamp.
- The **per-track** mpv spawn (`player.play`) did not set `CREATE_NO_WINDOW` on Windows (only the `play_file` path did), so every track started from the GUI flashed a black console window behind it. `play()` now uses the same `creationflags=0x08000000` as `doctor.py`/`library.py`/`play_file`, with two new regression tests in `tests/test_v030_fixes.py` (`N-player-2`).
- The mpv **video window** itself could still appear over the GUI: `_base()` sent `--no-video` but a user's own `mpv.conf` (e.g. `force-window=yes` or the pseudo-gui profile) re-enabled window creation even for audio-only playback. The player now sends `--force-window=no` on the top of every mpv command as well -- command-line options always override config files in mpv, so the bot's window policy can no longer be overridden. Covered by `N-player-3` tests.
- Scheme-less URLs (`youtube.com/watch?v=...`, `youtu.be/x`): `engine.resolve()` now prepends `https://` when the host matches `allowed_hosts` before the remote lookup (previously these were searched as library names and came back "not found"). An empty `!play` argument raises a friendly "nothing found" error instead of falling through to the library search.
- Router (`commands.handle`) now logs every received command at INFO (`command !<name> <arg> from <user>`, plus `admin` / blocked / cooldown drops), so the operator log shows what users actually requested and why a request was silently ignored.
- `_sender` retries a failed room send once after 2s; if the retry also fails it logs `send retry failed too, dropped:` and moves on instead of leaving the outbox stuck.
- UIA adapter (`adapters/uia.py`): all UIA/COM access is serialized behind a re-entrant `com_lock` (reader thread and sender no longer race); a failed chat read now drops `win = None` so the next poll re-attaches fresh instead of staying wedged with `An event was unable to invoke any of the subscribers` until restart. `send()` is a lock-wrapped wrapper around `_do_send` that clears cached controls on any exception.
- Background-send fast path: in `auto` mode, after 2 unconfirmed background sends in a row the bot skips the verify+fallback delay and goes straight to foreground paste, so announcements must not stack seconds of verify+fallback latency every track. `_send_bg` now writes text into the chat editor via UIA `ValuePattern.SetValue` before falling back to posted WM_CHAR (Chromium editors ignore posted keystrokes without focus), and foreground sends are verified too, with a WARNING when the line never appears in the room.
- `fmt_now`/`fmt_next`: a bad `msg_now`/`msg_next` template no longer raises — it falls back to the built-in text (a typo in the template can't kill the player-loop thread).
- `player.play()` now passes the resolved yt-dlp path (`ytdlp_path`, else yt-dlp next to mpv / PATH) to mpv's `--script-opts=ytdl_hook-ytdl_path` even when `ytdlp_path=""`, so title lookups and playback use the same yt-dlp.
- New `playlist.json` store (`playlist_file` config key, default `playlist.json`): tracks requested by users (`!play`, GUI request, `!load`) are appended to the file (deduplicated by source) and join the autoplay pool (random, looping); a missing or corrupt file is never fatal. New `!last` command (aliases `requested`, `ขอล่าสุด`) shows the most recently requested tracks; covered by `tests/test_play_flow.py`.

## 0.2.2
"Grand" GUI pass: a living, decorated now-playing stage.

### Added

## 0.2.5

### Added
- **Dynamic search resolution for playlist tracks**: Search-backed entries (`ytsearch1:...`) from starter playlist files are dynamically resolved to real YouTube URLs, verified video titles, and exact durations upon playback and via asynchronous lookahead queue preloading.
- **Automatic playlist update on resolve**: `PlaylistStore.update_source()` replaces resolved search queries in `playlist.json` with the real YouTube URL atomically, preventing repetitive search overhead on subsequent restarts.
- **Audio fade-in and fade-out**: Smooth volume ramping upon track playback start and skip/stop.
- **Dynamic loudness normalization**: Configurable dynamic audio normalization using FFmpeg `dynaudnorm` filter in mpv.
- **YouTube authentication & cookie support**: Optional `--cookies` file and `--cookies-from-browser` parameters passed securely to yt-dlp.
- **Dynamic voteskip threshold**: Optional dynamic quorum based on room participant count.
- **Per-user sliding rate limiting**: Monotonic sliding window cooldown and request limit to protect against chat flood.
- **Software Supply Chain Security**: Release workflow upgraded with automated CycloneDX SBOM generation and GitHub artifact attestation.

### Fixed
- **GUI ไม่ขึ้น (GUI won't open)**: `camfrog_autodj/__main__.py` — auto-discovery (`discover.apply()`) crashed with `ImportError` on `pywinauto.Desktop` before `App(eng).mainloop()` was reached, so the Tk window never appeared. Auto-discovery is now wrapped in `try/except` and logs a warning instead of crashing; `build_adapter()` failures fall back to `NullAdapter` so the GUI still opens without chat (user can run `--check`/`--discover` from inside it).
- **Camfrog adapter blocks GUI startup**: `camfrog_autodj/adapters/uia.py` `UiaAdapter.__init__()` called `resolve()` which polls up to 30s for a Camfrog window, blocking GUI launch. With `NullAdapter` fallback in `__main__.py`, this no longer blocks.
- **Playlist not in queue list box**: `camfrog_autodj/engine.py` `_load_all()` added `playlist.json` tracks to the autoplay *pool* (`add_pool`), but the GUI list box only shows the request *queue* (`add_request`). Playlist tracks are now added to `add_request` so they appear in the GUI and play before the autoplay pool. Dedupe against existing requests and history prevents re-queuing on restart.
- **Thread-safety data race on `e.current`**: `camfrog_autodj/commands.py` `_play()` read `e.current.source` outside `e.queue.lock`, racing with `_player_loop()` which writes `e.current`. Now read under the same lock.
- **Ungraceful shutdown**: `camfrog_autodj/engine.py` `shutdown()` did not wait for daemon threads. Thread references are now stored in `self._threads` and joined (5s timeout each) on shutdown.
- **Windows-only code crashes on Linux**: `camfrog_autodj/launcher.py`, `camfrog_autodj/tts.py`, `camfrog_autodj/winmsg.py` now call `_require_windows()` to raise a clear `RuntimeError` instead of crashing with obscure `ctypes`/`pywinauto` errors on non-Windows platforms.
- **`!load` path traversal**: `camfrog_autodj/commands.py` `_load()` now rejects absolute paths outside `music_dirs` (admin-only guard).
- **NSIS installer warnings**: `installer.nsi` — removed `docs\*.txt` file glob (no such files), removed unused `.onUninstSuccess` function, removed unused `GetDate` function (now called inline via `Call GetDate`), removed duplicate `Uninstall.lnk` shortcut, removed `SEC_SRC` section (Python source not shipped in installer). All 5 NSIS warnings eliminated.

### Changed
- `camfrog_autodj/engine.py`: `Engine.__init__` now accepts `cfg_path` (was missing, causing `TypeError` when `_run()` passed it). GUI buttons `do_discover()`/`do_check()` read `self.e.cfg_path`.

### Added
- `camfrog_autodj/adapters/__init__.py`: new `NullAdapter` — silent fallback when Camfrog cannot be reached; GUI stays open, chat degrades gracefully.
- `camfrog_autodj/engine.py`: `_threads` list tracking all daemon threads started by `start()`.

## 0.2.4

### Fixed
- `camfrog_autodj/adapters/uia.py` `_appeared()`: `norm_l` was referenced outside the `for l in new:` loop. When no new chat lines arrived, `norm_l` was never assigned, causing `UnboundLocalError` on every background chat send — messages retried endlessly (`send failed ... retrying once in 2s`). Moved the `bot_nick` match inside the loop so `norm_l` is always defined before use, and every new line is checked (not just the last one).
- `camfrog_autodj/adapters/uia.py` `_bg_fails`: consecutive-failure counter was read/written without a lock across reader and sender threads, causing a race condition. Now protected by `_bg_fails_lock`.
- `camfrog_autodj/adapters/uia.py` `messages()`: `self._view = None` was assigned outside `com_lock`, racing with `_lines()` which reads `self._view` inside the lock. Now assigned inside `com_lock`.
- `camfrog_autodj/winmsg.py`: three module-level functions were defined twice — `make_lparam` (lines 58 and 256), `pick_child` (lines 62 and 260), `show_noactivate` (lines 117 and 273). The second definition silently shadowed the first. Removed the duplicate block.
- `camfrog_autodj/webchat.py`: unused unpacked variable `node` → `_node` in `read_items()`.
- `camfrog_autodj/gui.py`: unused unpacked variables `r`/`lab` → `_r`/`_lab` in three `_vc` unpack sites; removed unnecessary `int(round(...))` in `px()`.
- `camfrog_autodj/visuals.py`: removed unnecessary `int(round(...))` in `rgb_to_hex()`.
- `camfrog_autodj/adapters/uia.py`: merged two `endswith()` calls into one with a tuple argument.
- `camfrog_autodj/doctor.py`: replaced unnecessary `dict(...)` call with a literal.
- `camfrog_autodj/engine.py`: replaced unnecessary `dict(...)` call with a literal in `snapshot()`.
- `camfrog_autodj/library.py`: replaced unnecessary `dict(...)` call with a literal in `_extract_exe()`.
- `camfrog_autodj/gui.py`: `add_files()` and `load_folder()` now check for `$DISPLAY`/`$WAYLAND_DISPLAY` before opening native file dialogs, and wrap in try/except — fixes hang on headless Linux.
- `camfrog_autodj/installer.nsi`: removed machine-specific `config.toml` from bundle (path hardcoded to one PC); config is now created by `install.ps1` on first run.
- `camfrog_autodj/tts.py`: **TTS did nothing with default config** — `eng.save_to_file()` and `eng.runAndWait()` were inside `if cfg.tts_voice:`, so with `tts_voice = ""` nothing was synthesised. Moved outside the `if`. Also added `TTS_TIMEOUT` (60s) so `synth()` no longer blocks forever if pyttsx3 is missing or hangs; each job independently imports pyttsx3 so the worker stays alive even if it's not installed.
- `camfrog_autodj/library.py`: **`ytsearch20:` autoplay sources always failed** — `is_url()` only matches `http://`/`https://`, so `ytsearch20:mandopop` was double-wrapped as `ytsearch1:ytsearch20:mandopop` and failed. Added `SEARCH_PREFIX` regex and `raw_target` parameter so operator-supplied `ytsearchN:` queries pass through unchanged. Also fixed `find_ytdlp()` to fall back to PATH yt-dlp when `mpv_path` is the default `"mpv"` (the previous code refused PATH lookup when mpv_path was set, ignoring a perfectly good yt-dlp on PATH).
- `camfrog_autodj/commands.py`: **`!play` from chat was not saved to `playlist.json`** — only admin/GUI requests were saved, so `!last` was always empty for chat requests. Added `e.playlist.add(tracks)` for chat requests too. Also fixed cooldown case-dodging (`"Bob"` and `"bob"` are now one person via `.lower()`) and `²` digit bypass in `!remove`/`!vol` (`isascii()` check).
- `camfrog_autodj/player.py`: **`mpv_timeout` killed every track longer than the timeout** — `p.wait(timeout=120)` capped total play time, cutting any track over 2 minutes. Changed to a grace period: `limit = duration + mpv_timeout`, checked via 0.5s polling loop; pauses are excluded from the countdown; unknown-duration (live) tracks have no limit. Added `POLL` constant and `_played()` helper.
- `camfrog_autodj/playlist.py`: **corrupt `playlist.json` was silently overwritten** — `load_playlist()` returned `[]` and `save_playlist()` would overwrite the bad file. Added `_unreadable()` check and `PlaylistStore.add()` now saves a `.corrupt-<timestamp>` backup before overwriting.
- `tests/test_hardening.py`: updated `FailingPlayer.play()` and `lambda` mocks to accept the new `duration` parameter on `MpvPlayer.play()`.

### Added
- GUI: `--discover` และ `--check` ปุ่มบน now-playing card (`🔍 ค้นหาห้องแชท` / `✓ ตรวจสอบการตั้งค่า`) ให้ผู้ดูแลระบบรัน auto-discovery และวินิจฉัยการตั้งค่าจากหน้าต่างเดสก์ท็อปโดยไม่ต้องเปิดเทอร์มินัล
- `installer.nsi`: รองรับหลายภาษาในตัวติดตั้ง (English + Thai) ผ่าน `MUI_LANGUAGE` macro; ไฟล์ `thai.nlf` รวมอยู่ใน repo (ต้องติดตั้งที่ `Contrib\Language\` ของ NSIS บนเครื่อง Windows ก่อนคอมไพล์)
- `camfrog_autodj/engine.py`: `Engine.__init__` no longer takes `cfg_path` (was an experiment, removed). Added `_speak_lock` so only one TTS clip plays at a time (overlapping TTS jobs would un-duck the music early). `load_source()` now recognises `ytsearchN:` queries as raw targets for autoplay sources.
- `camfrog_autodj/engine.py` shutdown order: `adapter.close()` before `exec.shutdown()` so sender threads release the adapter before it's closed.

### Testing
- Full suite: **97 passed, 1 skipped** (was 130 passed before test mock updates for the new `duration` parameter on `MpvPlayer.play()`).
- All command paths verified end-to-end via `--lang th --console` (Thai and English).

## 0.2.3
`make` on plain Windows PowerShell/cmd. **Automated Windows 11 installer (`install.ps1` / `install.bat`).**

### Added
- `install.ps1` / `install.bat`: Full-featured automated installer for Windows 11. Verifies OS, installs prerequisites (Python 3.11+, mpv, yt-dlp, VB-Cable) via winget or direct download, clones the project, installs Python dependencies, builds `AutoDJ.exe` with PyInstaller, creates `config.toml` with interactive prompts, creates Desktop/Start Menu shortcuts (including Config editor and Uninstaller), optional auto-start on login, and runs `AutoDJ.exe --check` for verification. Logs to `%TEMP%\autodj-install-<timestamp>.log`.

### Fixed
- `make help` (and every other target) failed on Windows with confusing cascading errors ("The system cannot find the path specified", then `awk` "CreateProcess ... failed") when `make` was installed but bash/awk/coreutils were not on PATH. `SHELL` no longer hard-codes the Linux path `/bin/bash` (now resolved via PATH, so it also works if Git Bash's `bash.exe` is on PATH without being at that exact path). More importantly, the Makefile now checks for `bash` up front and fails with ONE clear message explaining the two real options: run `make` from inside Git Bash, or skip `make` entirely and use `build.ps1` / `python -m pytest` directly (which is what `make` wraps anyway and needs no Unix tools at all).
- In this working tree the same Windows-`make` problem was solved a different way (never released in 0.2.3): every recipe that needs Unix utilities (awk/find/grep/cp) was rewritten as a `python -c` one-liner and `SHELL` now falls back to `cmd.exe /c` when `bash` is not on PATH, so `make` works from plain PowerShell/cmd (and `make build`/`build-clean`/`sign` call `powershell.exe` automatically from WSL2). This Makefile superseded the released fail-fast version and is kept here; `make help` keeps a documented target list in `README.md`.
- Building from WSL2: `make build` drives `build.ps1` via WSL interop's `powershell.exe`. On a machine that also has PowerShell 7, the inherited `PSModulePath` contains PS7 module dirs, PS 5.1 resolves the **PS7** `Microsoft.PowerShell.Security` first, that load fails its authorization check, the Certificate provider never registers and the sign step dies with `Cannot find drive: 'Cert'`. `build.ps1` and `tools/sign_exe.ps1` now deselect the PS7-only dirs at startup (PS 5.1 only; pwsh 7 itself is unaffected), so `make build` and `make sign` finish cleanly: `AutoDJ 0.2.3` smoke test, `signature: Valid (Signature verified.)`, DigiCert timestamp.
- The **per-track** mpv spawn (`player.play`) did not set `CREATE_NO_WINDOW` on Windows (only the `play_file` path did), so every track started from the GUI flashed a black console window behind it. `play()` now uses the same `creationflags=0x08000000` as `doctor.py`/`library.py`/`play_file`, with two new regression tests in `tests/test_v030_fixes.py` (`N-player-2`).
- The mpv **video window** itself could still appear over the GUI: `_base()` sent `--no-video` but a user's own `mpv.conf` (e.g. `force-window=yes` or the pseudo-gui profile) re-enabled window creation even for audio-only playback. The player now sends `--force-window=no` on the top of every mpv command as well -- command-line options always override config files in mpv, so the bot's window policy can no longer be overridden. Covered by `N-player-3` tests.
- Scheme-less URLs (`youtube.com/watch?v=...`, `youtu.be/x`): `engine.resolve()` now prepends `https://` when the host matches `allowed_hosts` before the remote lookup (previously these were searched as library names and came back "not found"). An empty `!play` argument raises a friendly "nothing found" error instead of falling through to the library search.
- Router (`commands.handle`) now logs every received command at INFO (`command !<name> <arg> from <user>`, plus `admin` / blocked / cooldown drops), so the operator log shows what users actually requested and why a request was silently ignored.
- `_sender` retries a failed room send once after 2s; if the retry also fails it logs `send retry failed too, dropped:` and moves on instead of leaving the outbox stuck.
- UIA adapter (`adapters/uia.py`): all UIA/COM access is serialized behind a re-entrant `com_lock` (reader thread and sender no longer race); a failed chat read now drops `win = None` so the next poll re-attaches fresh instead of staying wedged with `An event was unable to invoke any of the subscribers` until restart. `send()` is a lock-wrapped wrapper around `_do_send` that clears cached controls on any exception.
- Background-send fast path: in `auto` mode, after 2 unconfirmed background sends in a row the bot skips the verify+fallback delay and goes straight to foreground paste, so announcements no longer stall seconds per track. `_send_bg` now writes text into the chat editor via UIA `ValuePattern.SetValue` before falling back to posted WM_CHAR (Chromium editors ignore posted keystrokes without focus), and foreground sends are verified too, with a WARNING when the line never appears in the room.
- `fmt_now`/`fmt_next`: a bad `msg_now`/`msg_next` template no longer raises — it falls back to the built-in text (a typo in the template can't kill the player-loop thread).
- `player.play()` now passes the resolved yt-dlp path (`ytdlp_path`, else yt-dlp next to mpv / PATH) to mpv's `--script-opts=ytdl_hook-ytdl_path` even when `ytdlp_path=""`, so title lookups and playback use the same yt-dlp.
- New `playlist.json` store (`playlist_file` config key, default `playlist.json`): tracks requested by users (`!play`, GUI request, `!load`) are appended to the file (deduplicated by source) and join the autoplay pool (random, looping); a missing or corrupt file is never fatal. New `!last` command (aliases `requested`, `ขอล่าสุด`) shows the most recently requested tracks; covered by `tests/test_play_flow.py`.

## 0.2.2
"Grand" GUI pass: a living, decorated now-playing stage.

### Added
- The now-playing panel now has a drifting aurora backdrop (slow colour bands) with a twinkling starfield behind the record, and ~26 soft particles orbiting it that brighten and dim with the music.
- A burst of ~22 confetti pieces fires from the record whenever a new track starts (including the first).
- The whole window now has a thin border that glows pink in time with the music while a track plays, and fades out when paused/idle.
- The AUTODJ wordmark in the header has a soft duplicate-text glow behind it.
- `camfrog_autodj/visuals.py`: `aurora_offset`, `make_particles`/`particle_pos`, `confetti_burst`/`confetti_pos` (pure functions, unit-tested, no Tk needed to test them).

### Fixed
- An internal naming collision: the new window-border-glow state was stored under the same attribute (`self._glow`) already used for the vinyl's halo-ring canvas items, so turning on the border glow crashed the animation loop (`TypeError` mixing a float with a list) every frame while a track played. Caught by `tests/test_gui_logic.py` before release; renamed to `self._border_glow`.

## 0.2.1
Dev-convenience `Makefile` (cross-platform: Linux/macOS/WSL/Git-Bash with `make`; the Windows `.exe` is still built by `build.ps1`, which the Makefile just wraps).

### Added
- `Makefile` with targets for install, run (gui/console/headless), `check`/`discover`/`windows`/`say`, test (`test`, `test-v`, `test-one`, `coverage`), `lint`/`fmt`/`typecheck` (use `ruff`/`black`/`mypy` if installed, fall back gracefully otherwise), `build`/`build-clean`/`sign` (wrap `build.ps1`/`tools/sign_exe.ps1` on Windows; a clear message elsewhere), a one-shot `release` target (changelog check -> test -> build+sign -> package), `package` (zip the source tree), and housekeeping (`clean`/`clean-all`/`distclean`). `make help` lists everything.
- `make build`/`build-clean`/`sign`/`release` take `PFX=`, `PASSWORD=`, `THUMBPRINT=`, `SUBJECT=`, `NOSIGN=1` and pass them straight through to `build.ps1`'s own signing options (same env vars also still work). With none of these, `build.ps1` already signs automatically (self-signed certificate, created/trusted once) -- the Makefile does not change that default, it just exposes the same choices `build.ps1` always had.
- `tools/minipytest.py` and `tools/mutate.sh` are now part of the shipped project (previously only used ad hoc), so `make test` and `make mutation-smoke` work out of the box even before `pip install -e .[dev]`.
- `tools/package.py`: the zip-building logic `make package` uses.

### Fixed
- `tools/minipytest.py` resolved the project root incorrectly when given a single test file (`make test-one T=tests/x.py`): `camfrog_autodj` was not importable. Also did not understand pytest's `file.py::test_name` node-id syntax (silently ran zero tests). Both fixed.
- The Makefile's original `package` target built the zip with a multi-line heredoc inside a recipe; `make` runs each recipe line in its own shell by default, so the heredoc never worked (`make package` failed every time). Moved into `tools/package.py`.
- `make coverage` printed a raw `No module named coverage` twice instead of a clear message when the optional `coverage` package is not installed.

## 0.2.0
Audit release (details and evidence in `AUDIT.md`) plus a new GUI.

### Fixed
- **Bot reacted to its own chat lines.** The `!help` reply began with `!play ...`; when `bot_nick` did not match the account's real nick it was executed as a play request. Help now starts with a label, wrapped continuation lines can no longer start with the command prefix, and lines the bot posted are recognised when they come back from the room.
- **A failing track could flood the room.** With mpv missing or yt-dlp unavailable and a non-empty autoplay pool the player retried in a tight loop (measured: ~9,900 attempts and ~29,700 queued chat messages in half a second). Failures now back off (1, 2, 4 ... 30 s), are announced at most 3 times in a row, and the reason from mpv's own log is written to the log.
- **`No module named 'yt_dlp'` in AutoDJ.exe.** Lookups use `yt-dlp.exe` (next to mpv, on PATH, or `ytdlp_path`) when present and fall back to the module; if neither exists the room gets a short message and the log says exactly what to do. `build.ps1` now refuses to build when a required package is missing, bundles yt-dlp with `--collect-all`, builds without UPX, and smoke-tests the exe.
- **`config.toml` errors crashed with a traceback.** Now: the offending line with a `^`, a hint, exit code 2. Unknown settings get "did you mean", wrong types/values (`admins = "nick"` used to become the admin set `{n,i,c,k}`), bad regexes and out-of-range numbers are reported by name.
- `!remove` could remove a different request if the queue shifted (and so could the GUI's Remove button): removal is now by identity.
- A user could exceed `max_requests_per_user` by firing requests while earlier lookups were still running: limits are re-checked atomically after the lookup.
- Auto-discovery could write an unreadable config (and wrote it non-atomically): values are escaped, the result is validated before saving, the write is atomic.
- `pause`/`resume` no longer claim success when mpv's control pipe was not ready.
- GUI: one exception in the polling loop froze the window forever; the chat box grew without limit.
- Control characters in text sent to the room (typed as keystrokes) are stripped. Reloading a folder no longer duplicates the autoplay pool. The send throttle wakes up at shutdown. More worker threads, so a slow lookup does not block `!skip`.

### Added
- `--check` (diagnose mpv, yt-dlp, JS runtime hint, folders, admins, optional packages, Camfrog window), `--version`, `--log-file` / `log_file`.
- `!history` (`!ประวัติ`), `!block` / `!unblock` and `blocked_users`, refusal of songs already queued or playing, `ytdlp_path`, `poll_interval`.
- GUI redesign: neon dark theme, spinning record, animated equaliser, gradient progress, custom volume slider, ON AIR light, Queue / History / Chat tabs, shuffle/repeat chips, keyboard shortcuts, mpv-missing banner, HiDPI + dark title bar on Windows.
- Tests: 78 (was 32), including regression tests for each fix, a strict fake Tk for the GUI logic, and a pre-flight for the build environment. CI workflow, `.gitignore`, pytest settings.

### Changed
- Test fixture `make()` now returns a distinct source per request (the duplicate guard needs it).
