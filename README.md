# CamfrogAutoDJ

Music bot for a Camfrog room: YouTube + local mp3/mp4 autoplay, `!commands`, now/next announcements, talk to room. Bot replies and GUI in English or Thai.

## What's new in 0.3.0 (Enterprise Production Release)
Highlights: **Enterprise-grade exception hierarchy** with structured error codes, **Circuit breaker** for playback resilience, **Per-nick chat rate limiting**, **Health check endpoint** for monitoring, **C901 complexity fixes** in chat/player loops, **IM viewer GUI** with settings, **IM auto-reply** with cooldown, **Camfrog RE integrations**: gift detection, avatar change detection, status indicators, upgrade/payment alerts, name color tracking. Full list: `CHANGELOG.md`.

### Enterprise Architecture Improvements
1. **Exception Hierarchy** (`camfrog_autodj/exceptions.py`): 20+ structured exception types with machine-readable codes (`config.error`, `chat.send_failed`, `player.hung`, `security.unauthorized`, etc.) and contextual metadata. All exceptions inherit from `AutoDJError` for unified catching.
2. **Circuit Breaker** (engine.py): Tracks consecutive playback failures; opens after 5 failures, pauses playback for 60s, then half-opens for recovery. Prevents cascading failures on broken tracks/yt-dlp issues.
3. **Chat Send Circuit Breaker**: Suspends chat sends after 10 consecutive delivery failures to prevent API bans.
4. **Per-Nick Rate Limiting**: Sliding window (20 messages/60s per nick) prevents chat flooding. Admins exempt.
5. **Health Check Endpoint** (`engine.health_check()`): Returns structured dict with mpv availability, circuit breaker state, send suspension, queue depth, IM viewer status — safe for monitoring dashboards.
6. **Code Quality**: C901 complexity refactored (`_chat_loop` split into `_handle_im`, `_handle_room_message`, `_should_ignore_message`), all 375 tests pass, ruff/mypy/format/shellcheck clean.

### New in 0.3.0
1. **IM Viewer GUI**: New IM tab in the desktop window shows private/instant messages with polling. Settings dialog includes IM viewer enable/disable, auto-reply message, cooldown, and room presence requirement.
2. **IM Auto-Reply**: Configurable auto-reply to private messages with per-user cooldown (default 30s). Uses `[IM]` prefix in sent replies.
3. **Camfrog Gift Detection**: Detect virtual-gift messages in room chat (`GIFT_RECEIVED`, `room_gift_message`, `camfrog://gift`, etc.) and announce them. Config-gated: `gift_announce_enabled`. (see `docs/camfrog-re/08-feature-gift.md`)
4. **Camfrog Avatar Change Detection**: Detect avatar change messages in room chat (`updateAvatarMessage`) and announce them. Config-gated: `avatar_change_enabled`. (see `docs/camfrog-re/16-user-icon-avatar.md`)
5. **Camfrog Status Indicators**: Detect user status changes in room chat (online/away/busy/invisible/admin/moderator/owner) and announce them. Config-gated: `status_indicator_enabled`. (see `docs/camfrog-re/14-png-assets.md`)
6. **Camfrog Upgrade/Payment Alerts**: Detect upgrade/payment-required status text and alert admin. Config-gated: `status_alert_enabled`. (see `docs/camfrog-re/07-upgrade-logic.md`, `09-payment.md`)
7. **Camfrog Name Color Tracking**: Read nickname color (`color: #RRGGBB`) from incoming chat HTML for GUI preview (read-only; AutoDJ cannot set name color). (see `docs/camfrog-re/15-name-color.md`)

### New in 0.2.8
1. **Font/Style Customization (GUI Preview Only)**: New `message_style` config section with font family, size, color, bold, italic, underline. Live preview in Settings tab. **Note**: Camfrog desktop client does NOT support rich text in outgoing messages — sent messages are always plain text via UIA. This feature is for the GUI preview panel only.
2. **Admin Greeting**: Greet admin on first message in session with configurable message and cooldown (default 1 hour).
3. **Delete History**: Admin command `!deletehistory <all|N>` to clear history or remove oldest N entries.
4. **IM-Only Play Commands**: `!play`, `!request`, `!req`, `!p`, `!เล่น`, `!ขอเพลง`, `!เล่นเพลง` now only work via private message (IM). Room users must DM the bot. Admins can still use in room.
5. **Autoplay Idle Timeout**: After 30 minutes (configurable) with no user requests, bot switches to autoplay pool. New `!play` immediately exits autoplay mode.
6. **New Thai Aliases**: `!ขอเพลง` (request song), `!เล่นเพลง` (play song).
7. **Auto-Reply**: Every 60 seconds from `ads-list.json` (configurable).
8. **REA Reverse Engineering**: Documented Camfrog font logic (GDI imports, chat/IM font settings, HTML rendering for display only).
9. **Mic Mute/Unmute**: Admin commands `!mute` / `!unmute` to mute/unmute the mic (config-gated: `admin_mute_mic`, `admin_unmute_mic`).
10. **Block/Unblock Bot**: Admin commands `!blockbot` / `!unblockbot` to block/unblock bots (config-gated: `admin_block_bot`, `admin_unblock_bot`).
11. **Kick/Ban/Unban User**: Admin commands `!kick` / `!ban` / `!unban` (config-gated: `admin_kick_user`, `admin_ban_user`, `admin_unban_user`).
12. **Punish User/Bot**: Admin commands `!punish` / `!punishbot` (config-gated: `admin_punish_user`, `admin_punish_bot`).
13. **Delete Message**: Admin command `!delete <msg id>` to delete a message by ID (config-gated: `admin_delete_message_enabled`).
14. **Welcome Message**: Welcome message feature with configurable text (config-gated: `welcome_message_enabled`).
15. **Camfrog Gift Detection**: Detect virtual-gift messages in room chat (`GIFT_RECEIVED`, `room_gift_message`, `camfrog://gift`, etc.) and announce them. Config-gated: `gift_announce_enabled`. (see `docs/camfrog-re/08-feature-gift.md`)
16. **Camfrog Avatar Change Detection**: Detect avatar change messages in room chat (`updateAvatarMessage`) and announce them. Config-gated: `avatar_change_enabled`. (see `docs/camfrog-re/16-user-icon-avatar.md`)
17. **Camfrog Status Indicators**: Detect user status changes in room chat (online/away/busy/invisible/admin/moderator/owner) and announce them. Config-gated: `status_indicator_enabled`. (see `docs/camfrog-re/14-png-assets.md`)
18. **Camfrog Upgrade/Payment Alerts**: Detect upgrade/payment-required status text and alert admin. Config-gated: `status_alert_enabled`. (see `docs/camfrog-re/07-upgrade-logic.md`, `09-payment.md`)
19. **Camfrog Name Color Tracking**: Read nickname color (`color: #RRGGBB`) from incoming chat HTML for GUI preview (read-only; AutoDJ cannot set name color). (see `docs/camfrog-re/15-name-color.md`)

## Makefile (optional, for Linux/macOS/WSL/Git-Bash)
`make help` lists every target: `install`, `run-gui`/`run-console`/`run-headless`, `check`/`discover`/`windows`/`say`, `test`/`test-one`/`coverage`, `lint`/`fmt`/`typecheck`, `build`/`build-clean`/`sign` (wrap `build.ps1` -- still Windows PowerShell only; a clear message elsewhere), `release` (test -> build+sign -> package, one command), `package`, `clean`/`clean-all`/`distclean`.
`build.ps1` always signs by default (self-signed cert, created and trusted once); on top of that the Makefile passes through the same choices `build.ps1` already has: `make build PFX=cert.pfx PASSWORD=secret`, `make build THUMBPRINT=<hex>`, `make build SUBJECT="CN=My Company"`, `make build NOSIGN=1` (or the env vars `build.ps1` reads: `AUTODJ_PFX`, `AUTODJ_PFX_PASSWORD`, `AUTODJ_CERT_THUMBPRINT`). On Windows, run these from PowerShell with `make` installed (e.g. via `choco install make` or Git Bash), or just call `build.ps1` directly -- the Makefile is a convenience wrapper, not a requirement. The recipes are deliberately `python -c`/plain-command based (no awk/find/grep/cp/sed) and `SHELL` falls back to `cmd.exe /c` when `bash` is not on PATH, so plain PowerShell/cmd works too; from WSL2, `make build`/`build-clean`/`sign` automatically call the Windows `powershell.exe`. If `make` still not work on your shell, skip it: `python -m pip install -e . pyinstaller` then `.\build.ps1` builds and signs `AutoDJ.exe`, and `python -m pytest` runs the tests directly.

## Setup (Windows)
1. Python 3.11+, [mpv](https://mpv.io), a virtual audio cable (e.g. VB-Cable).
2. `pip install -e .` and put `yt-dlp.exe` in the same folder as `mpv.exe` (or on PATH): mpv needs it to play YouTube. Set `mpv_path` to the full path. Then run `camfrog-autodj --check` (or `AutoDJ.exe --check`): it tells you in plain words what is still missing.
3. Camfrog mic = cable output. `audio_device` in config = cable input (`mpv --audio-device=help`).
4. `copy config.example.toml config.toml`: set `admins`, `bot_nick`, `music_dirs`, `lang`.
5. Open the room window and start AutoDJ: with `auto_discover = true` it finds the room window and chat/input controls and writes `window_title_re`, `view_*`, `input_*` to `config.toml` (backup `config.toml.bak`). `--discover` does just that and exits; `--no-discover` skips it. `--windows` lists every visible window with its exe (to see what Camfrog looks like); `--dump <title_re>` prints a window's control tree. `--say "test"` sends one line into the room and exits (checks that chat sending works). Manual fallback: `python tools/inspect_ui.py`.
6. Run:
   - `camfrog-autodj --gui` desktop window
   - `camfrog-autodj` headless
   - `camfrog-autodj --console` try commands without Camfrog (`--lang th`)

## GUI
A dark "studio" window: a spinning record and an animated equaliser while a track plays (the equaliser is decorative, it does not analyse the audio), a gradient progress bar, round Pause/Skip buttons, a volume slider, an ON AIR light, and shuffle / repeat chips. The right-hand panel has three tabs: **Queue** (remove/clear), **History** and **Room chat** (say in chat, speak with TTS). Add by URL / song name / path, load a folder, add files. TH / EN pills switch the language live.
Keys: `Space` pause/resume (when no text box has focus), `Ctrl+Right` skip. A red banner appears if `mpv` cannot be found. Display scaling (125 % / 150 %) is handled; the title bar follows Windows dark mode on recent Windows 10/11.

## Commands (prefix `!`; Thai aliases in brackets)
Everyone: `np` (เพลงนี้), `next` (ถัดไป), `queue` (คิว), `history` (ประวัติ), `voteskip` (โหวตข้าม), `remove <n>` (ลบ), `help` (ช่วยเหลือ), `mute` (ปิดไมค์), `unmute` (เปิดไมค์), `welcome` (ต้อนรับ).
Requester/admin: `skip` (ข้าม).
Admin: `pause` (หยุดชั่วคราว), `resume` (เล่นต่อ), `vol` (เสียง), `shuffle` (สุ่ม), `repeat` (วนซ้ำ), `clear` (ล้างคิว), `load` (โหลด), `say` (พูด), `speak` (ออกเสียง), `block <nick>` (บล็อก) / `unblock <nick>` (เลิกบล็อก), `blockbot <nick>` (บล็อกบอท) / `unblockbot <nick>` (เลิกบล็อกบอท), `kick <nick>` (เตะ), `ban <nick>` (แบน), `unban <nick>` (เลิกแบน), `punish <nick>` (ลงโทษ), `punishbot <nick>` (ลงโทษบอท), `deletehistory <all|N>` (ลบประวัติ), `delete <msg id>` (ลบข้อความ), `welcome <text>` (ต้อนรับ): a blocked nick's commands are ignored silently (admins cannot be blocked; also settable as `blocked_users` in config).

**Play commands (`!play`, `!request`, `!req`, `!p`, `!เล่น`, `!ขอเพลง`, `!เล่นเพลง`) now only work via IM (private message).** Room users must DM the bot. Admins can still use in room.

Non-admins: YouTube links only, 1 track, `max_duration`, no live, `max_requests_per_user`, and a song already queued or playing is refused. Name requests search `music_dirs` first, then YouTube.

**Requested songs play immediately:** `!play` inserts at the front of the queue so the song plays next. If no user requests arrive within `autoplay_idle_timeout` (default 30 seconds), AutoDJ switches to the autoplay pool automatically. A new `!play` request immediately exits autoplay mode.

## Auto launch
`auto_launch = true` starts `camfrog_exe`, opens `join_uri_template` for `room`, then waits for `window_title_re`. It does not call the control-server API. If the control-server agent already launches/joins Camfrog, keep `auto_launch = false`: AutoDJ waits for the room window.

## Sending to the room in the background
`send_mode` in config.toml: `background` posts the text (and a click + Enter) straight to the chat window's own handle, so Camfrog stays behind your other windows and your keyboard/clipboard are untouched. `foreground` is the old way (bring Camfrog up, paste, Enter; now restores your previous window and clipboard). `auto` (default) tries background, checks the line appeared in the room (`send_verify`), and only then falls back to foreground. Keep Camfrog un-minimised or on another desktop; a minimised window is restored without taking focus. Test with `AutoDJ.exe --say "test" -v`.

## GUI copy/paste
Ctrl+C/V/X/A now work on a Thai keyboard layout too (Tk only matched Latin keys), the chat log can be selected and copied, and every text box has a right-click menu (Cut/Copy/Paste/Select all).

## Build + sign AutoDJ.exe (one script)
`python -m pip install -e . pyinstaller`, then in PowerShell: `.\build.ps1` (or double-click `build_exe.bat`, same thing).
It first verifies that every package the exe must contain (yt-dlp, mutagen, pyttsx3, pywinauto, ...) is installed in the Python it will use (`tools\check_build_env.py`; a missing one used to give an exe that started fine and failed later with `No module named 'yt_dlp'`), checks the project, builds `dist\AutoDJ.exe` with `app.ico` and `version_info.txt` (company ZEAZDEV COMPANY LIMITED), copies `config.toml`, signs the exe (SHA256 + timestamp) and prints the signature status and SHA256.
- `-Clean` wipes `build\`, `dist\`, `AutoDJ.spec` first (use after changing icon/version/options). `-NoSign` builds only.
- Certificate, in order: `-Pfx file.pfx -Password ...` (or env `AUTODJ_PFX`, `AUTODJ_PFX_PASSWORD`), `-Thumbprint <hex>` (or env `AUTODJ_CERT_THUMBPRINT`), otherwise a self-signed cert for `-Subject` is reused or created once in your user store and trusted on this PC (one Windows confirmation dialog). It also writes `cert\autodj-codesign.cer` for other PCs.
- A self-signed cert is only trusted where that `.cer` is imported. Public distribution without SmartScreen warnings needs a real code-signing certificate (OV/EV or Azure Trusted Signing), then use `-Pfx`.
- The exe is built without UPX (fewer antivirus false positives) and started once with `--version` as a smoke test. `AutoDJ.spec` mirrors the options in `build.ps1`; edit `build.ps1`, not the spec.
- Close `AutoDJ.exe` before building (it cannot be rebuilt or signed while running). `camfrog_autodj/__init__.py` must contain only `__version__`.

## Automated Windows 11 Installer (one click)
**New in 0.2.6**: `install.ps1` / `install.bat` — a full-featured automated installer for Windows 11.
It handles the entire setup end-to-end:
1. **Verifies Windows 11** (Build 22000+)
2. **Installs prerequisites** via winget (or direct download):
   - Python 3.11+
   - mpv player
   - yt-dlp
   - VB-Cable virtual audio driver (optional, with guided download)
3. **Clones the project** from GitHub (or uses existing directory)
4. **Installs Python dependencies** (editable mode with dev/build extras)
5. **Builds `AutoDJ.exe`** with PyInstaller (optionally signed)
6. **Creates `config.toml`** from template with interactive prompts for bot nick, admin, music folder
7. **Creates shortcuts**: Desktop, Start Menu, Config editor, Uninstaller
8. **Optional auto-start** on login (`-AutoStart`)
9. **Runs verification** (`AutoDJ.exe --check`)

**Usage:**
```powershell
# Full interactive install (run from project folder or after cloning)
.\install.ps1

# Custom directory, auto-start, verbose
.\install.ps1 -ProjectDir "D:\AutoDJ" -AutoStart -Verbose

# Skip build (use pre-built), force reinstall deps
.\install.ps1 -NoBuild -Force

# Or double-click install.bat (passes args through)
```
**Requirements:** Windows 11, PowerShell 5.1+, Administrator rights for VB-Cable install.  
**Log file:** `%TEMP%\autodj-install-<timestamp>.log`  
**Uninstall:** Start Menu → CamfrogAutoDJ → Uninstall, or run `uninstall.ps1` in the project folder.

## Chat reader (web view)
Messages are split at the avatar images of the room's history pane, so date headers, system lines and bodies that look like a time ("10:30") no longer corrupt parsing. `web_strict_body = false` restores joining of adjacent text. Regression test: `tests/test_webchat_dump.py` (shaped after a real room dump).

## Troubleshooting
- **`Cannot start: ... TOML syntax error`**: the message shows the offending line of `config.toml` with a `^` marker. Typical causes: a note or console output pasted into the file (for example the `Thumbprint: ...` line printed by `tools\make_cert.ps1`): delete it or put `#` in front. Or copy `config.example.toml` over `config.toml`. A misspelt setting is reported with a "did you mean" hint.
- **Nothing plays / "Could not play"**: run `AutoDJ.exe --check`. The log also shows mpv's own reason (for example `[ytdl_hook] ERROR: ...`). After 3 failed tracks in a row the bot stops announcing failures in the room and backs off (1, 2, 4 ... 30 s) so a broken setup cannot flood the chat.
- **`YouTube lookup is unavailable right now`** (in the room) / `yt-dlp not found` (in the log): put `yt-dlp.exe` next to `mpv.exe`, or set `ytdlp_path`, or rebuild with `build.ps1` (which now refuses to build without the `yt_dlp` package).
- **YouTube lookups started failing after working for weeks**: update yt-dlp (`yt-dlp -U`; if you only use the bundled module, rebuild after `pip install -U yt-dlp`). Recent yt-dlp versions may also want a JavaScript runtime such as deno on PATH; `--check` mentions it when none is found.
- **The bot answers its own help text / loops**: fixed in 0.2.0 (lines the bot posts are recognised by their text); still set `bot_nick` to the nickname the bot chats as so the GUI log labels them correctly.
- **High CPU**: raise `poll_interval` (default 0.5 s).
- **Need a log to send to someone**: `AutoDJ.exe --log-file autodj.log` (or `log_file` in config).

## Caveats
- No public Camfrog bot API. Chat read/send is UI Automation (`adapters/uia.py`): control indexes and `line_regex` must be tuned per Camfrog version.
- Tested (325 passed, `python -m pytest -q -p no:faulthandler -p no:cacheprovider`): queue, commands EN/TH, chat diff, parsing, launcher flow (mocked), config validation, failure/echo/limit regressions (`tests/test_hardening.py`), GUI logic against a strict fake Tk (`tests/test_gui_logic.py`), an end-to-end run of the real CLI with a fake mpv, and all Thai/English command paths (`!ช่วยเหลือ`, `!เล่น`, `!เพลงนี้`, `!ข้าม`, `!บล็อก`, `!คิว`, `!ประวัติ`, `!สุ่ม`, `!วนซ้ำ`, `!เสียง`, `!ล้างคิว`, `!พูด`, `!ออกเสียง`, `!โหลด`, `!บล็อก`, `!เลิกบล็อก`, `!โหวตข้าม`, `!ลบ`, `!np`, `!ถัดไป`).
- Not tested: real Camfrog, mpv, yt-dlp, TTS (Thai voice must be installed in Windows), Windows launch/URI, how the new GUI actually looks on screen (the real-Tk smoke test `test_gui_smoke` runs wherever a display exists), `build.ps1`.
- Check room rules and Camfrog terms before running a bot.
