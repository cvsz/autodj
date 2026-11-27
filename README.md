# AutoDJ

Music bot for a Camfrog room: YouTube + local mp3/mp4 autoplay, `!commands`, now/next announcements, talk to room. Bot replies and GUI in English or Thai.

## What's new in 0.3.21

- The bot's messages reach the room again while someone is using the PC: background sends were typed into the wrong window and silently lost.

## What's new in 0.3.20

- When Camfrog is switched to the room list, the bot selects the room tab again by itself (after 45 s, only while nobody uses the PC), so room chat and private messages keep coming in.
- Old private messages that Camfrog redraws when the room tab comes back are not run again.

## What's new in 0.3.19

- Private messages now reach the bot and the IM tab: this Camfrog shows them inside the room chat ("ข้อความส่วนตัวจาก <nick>"), not in separate IM windows.
- Private messages from the room's bots are shown in the IM tab only: never answered, never run as commands.

## What's new in 0.3.18

- Answering an IM no longer pauses reading the room (IM replies are sent by their own worker).
- Settings saved while the bot runs now reach the chat reader at once (patterns, poll interval, send mode).
- Background sending is tried again 30 minutes after it was paused.
- Room presence and the dynamic voteskip count use recently seen nicks only.

## What's new in 0.3.17

- The room's own bots (any nick ending in "bot", e.g. ZeazBot, CloudBot) are never greeted: no welcome, no admin greeting, no mic greeting. New settings `greeting_ignore` (nick list) and `greeting_ignore_regex` (default `(?i)bot$`, `""` turns it off).
- Auto ads wait while the Camfrog room chat is not open instead of being dropped.
- New **Settings → Ads list…** editor for `ads-list.json`; the bot reloads it without a restart.
- Private messages (IM) from a chat window that opened while the bot was running are read again (a window whose chat pane was still loading was ignored for good).

## What's new in 0.3.16

- Requested songs are no longer cut off in their last seconds or logged as failed when the stream started late or buffered.

## What's new in 0.3.15

- **Full installer:** built with the `mpv\` folder present, the installer carries the whole folder (mpv, yt-dlp, `_internal\`, the VB-CABLE setup files) and installs it by default; the silent install (`/S`) no longer stops on a console or a dialog, and uninstalling removes everything it added. See docs/WINDOWS_BUILD.md.
- The log says what closed the AutoDJ window (a person, or another program).
- Songs that already played are no longer queued again when Camfrog re-renders the room chat.

0.3.14 carried the 0.3.11 changes. v0.3.11 and v0.3.12 were never released (their release runs failed before publishing); v0.3.13 was published but its exe lacked the optional hot-reload and webhook packages. Use 0.3.14.


- **AI answers only `!ai ask <question>`** (Thai `!เอไอ ถาม ...`, everyone). `ai_enabled = true` by default, but the AI stays off until `ai_api_key` is set (Settings → AI API key, masked). Ordinary room chat is never sent to the AI endpoint (NVIDIA by default).
- **Room messages are delivered reliably:** Ctrl+V works with the Thai keyboard layout, nothing is typed while Camfrog shows its room list or another tab, the bot waits until nobody is typing on the bot PC, and it never types into another application. "send ok" is logged only when the line really appeared in the room.
- **Mic greeting from a room bot:** a trusted bot's announcement (`mic_notice_senders`, e.g. ZeazBot's "<nick> กำลังรับไมค์") greets the user who took the mic; `mic_greeting_ignore` skips the streaming account.
- **Opening the room after start works:** AutoDJ attaches to the room window when it opens later.
- **Only one AutoDJ per config;** `AutoDJ.exe` without arguments opens the GUI; the bot never greets its own account.
- **Security:** auto-update accepts only an `AutoDJ.exe` signed by the pinned ZEAZDEV certificate; probe-account store keys are derived from the passphrase (not stored beside the data); admin targets are single tokens; local config backups are no longer tracked; Settings masks the AI key and webhook secret.

## What's new in 0.3.10

- **Mic/DJ greeting:** when the room shows `<nick> is now speaking` (or `<nick> กำลังรับไมค์`), AutoDJ announces "{user} is now the DJ." once per `mic_greeting_cooldown` (300 s). Only whole notice lines from that user count, so ordinary chat ("who is the dj?") never triggers it. Settings: `mic_greeting_enabled`, `mic_greeting_message` ("" = localized default), `mic_greeting_cooldown` — also in the Settings dialog.
- **`!ai help`** sends the full command list to you by IM; `!ai` alone shows the AI status.
- **Default `bot_nick` is `AutoDJ`.**
- **Duplicate-message suppression:** identical lines re-dumped by Camfrog after a reconnect no longer run the same command several times (3 s per-user window).
- **Settings dialog:** `user_request_limit` and `rate_limit_window` are now editable.
- **Log paths support `$APPDATA`/`~`** (`log_file`, `log_path`).
- **Installer:** bundled mpv + yt-dlp install to `%APPDATA%\AutoDJ\mpv` (never `%APPDATA%\mpv`, mpv's own config folder, which the uninstaller would have wiped). `make installer` always packages the current `config.example.toml`.
- **Fixes:** auto-discover's corrupted-cache cleanup no longer deletes part of the comtypes package; a line the bot posts twice is no longer handled as a user message on its second echo; the Windows prerequisite checks (NSIS / mpv / PyInstaller) really check again.

## What's new in 0.3.9

- **Default song waits a real 30 seconds:** after the last requested song finishes, AutoDJ waits `autoplay_idle_timeout` (30 s) for a new request before the default song (`default_track`) plays. It used to start at once after any request longer than 30 s.
- **Private IM replies actually go out:** replies ("กรุณาเข้าห้อง camfrog:join:{room} ก่อนขอเพลงครับ" (ตั้งค่าได้ที่ `im_join_room_message`) for users outside the room, IM auto-reply) are sent in the user's IM window and never in the room.
- **No false status announcements:** ordinary chat such as "anyway" or a quote mentioning an "owner" no longer makes the bot announce "X is now away" / "X is the room owner".
- **mpv.exe ends when AutoDJ ends,** even after End task or a crash. The installer also closes a running AutoDJ before upgrading or uninstalling.
- **Help → About** shows the version and "camfrog:add:Seaza Dev @ZEAZDEV COMPANY LIMITED".
- The chat loop no longer dies when Camfrog's room window is still loading, and messages dropped while Camfrog is closed are no longer logged as sent.
- AI defaults use the NVIDIA API catalog (`nvidia/llama-3.3-nemotron-super-49b-v1.5`); AI stays off until `ai_api_key` is set. The Python package is now `autodj` (`python -m autodj`).

Full list: `CHANGELOG.md`.

## What's new in 0.3.8 (hotfix)

- **Fixes a freeze on the first private message:** with IM auto-reply on (the default), the bot's chat loop and the whole window locked up when the first IM arrived. Found in a live Camfrog test.
- **IM viewer:** private messages now appear in the IM tab, including the first message of a new chat window.
- **GUI:** Skip/Prev no longer freeze the window, and Discover works in the installed exe.

Full details: `CHANGELOG.md`.

## What's new in 0.3.7 (deep audit fixes)

Logic and security fixes from a full code audit:

- **Webhook:** `/say`, `/shuffle` and `/repeat` work again (they always returned 422). Request bodies are now size-capped, and a client disconnect no longer pins a CPU core.
- **Playback:** a queue holding only songs that just failed no longer silences the room; the autoplay pool or default song plays meanwhile.
- **Requests:** a duplicate request is reported as "already queued" instead of being falsely announced; `!prev` always re-queues.
- **Player:** mpv position and property queries no longer fail spuriously.
- **Library:** scans skip Windows junction loops.
- **Private messages:** IM messages are now read, and a nickname such as `[IM]Admin` can no longer impersonate an admin.
- **Updater:** the update script works with installs in `Program Files (x86)`, paths containing `%`, and non-ASCII paths.

Full details: `CHANGELOG.md`.

## What's new in 0.3.6 (zPlayer GUI theme)

The desktop GUI now ships a TkinterEP-inspired theme system with three built-in palettes — `zplayer-dark` (default studio look), `zplayer-neon` and `zplayer-light`. Pick one with `ui_theme` in `config.toml` or from the Settings panel. The now-playing dashboard has a larger title, separate up-next preview, a Previous transport button (`Engine.prev()`), and refreshed progress/volume styling. `welcome_message_delay` can hold the room greeting for a few seconds. All version sources are synchronized to 0.3.6. Full details: `CHANGELOG.md`.

## What's new in 0.3.0 (Enterprise Production Release)
Highlights: **Enterprise-grade exception hierarchy** with structured error codes, **Circuit breaker** for playback resilience, **Per-nick chat rate limiting**, **Health check endpoint** for monitoring, **C901 complexity fixes** in chat/player loops, **IM viewer GUI** with settings, **IM auto-reply** with cooldown, **Camfrog RE integrations**: gift detection, avatar change detection, status indicators, upgrade/payment alerts, name color tracking. Full list: `CHANGELOG.md`.

### Enterprise Architecture Improvements
1. **Exception Hierarchy** (`autodj/exceptions.py`): 20+ structured exception types with machine-readable codes (`config.error`, `chat.send_failed`, `player.hung`, `security.unauthorized`, etc.) and contextual metadata. All exceptions inherit from `AutoDJError` for unified catching.
2. **Circuit Breaker** (engine.py): Tracks consecutive playback failures; opens after 5 failures, pauses playback for 60s, then half-opens for recovery. Prevents cascading failures on broken tracks/yt-dlp issues.
3. **Chat Send Circuit Breaker**: Suspends chat sends after 10 consecutive delivery failures to prevent API bans.
4. **Per-Nick Rate Limiting**: Sliding window (20 messages/60s per nick) prevents chat flooding. Admins exempt.
5. **Health Check Endpoint** (`engine.health_check()`): Returns structured dict with mpv availability, circuit breaker state, send suspension, queue depth, IM viewer status — safe for monitoring dashboards.
6. **Code Quality**: C901 complexity refactored (`_chat_loop` split into `_handle_im`, `_handle_room_message`, `_should_ignore_message`), all 336 tests pass, ruff/mypy/format/shellcheck clean.
7. **Webhook API Refactor** (`autodj/webhook/`): Eliminated global mutable state; dependency injection via FastAPI `app.state`; `RawBodyMiddleware` captures raw request body for HMAC verification; Pydantic request models (`PlayRequest`, `VolumeRequest`) for automatic validation; Prometheus `/webhook/metrics` endpoint; lazy FastAPI imports (optional dependency); all 13 tests pass.

### New in 0.3.0
1. **IM Viewer GUI**: New IM tab in the desktop window shows private/instant messages with polling. Settings dialog includes IM viewer enable/disable, auto-reply message, cooldown, and room presence requirement.
2. **IM Auto-Reply**: Configurable auto-reply to private messages with per-user cooldown (default 60s, min 10s). Uses `[IM]` prefix in sent replies.
3. **Camfrog Gift Detection**: Detect virtual-gift messages in room chat (`GIFT_RECEIVED`, `room_gift_message`, `camfrog://gift`, etc.) and announce them. Config-gated: `gift_announce_enabled`. (see `docs/camfrog-re/08-feature-gift.md`)
4. **Camfrog Avatar Change Detection**: Detect avatar change messages in room chat (`updateAvatarMessage`) and announce them. Config-gated: `avatar_change_enabled`. (see `docs/camfrog-re/16-user-icon-avatar.md`)
5. **Camfrog Status Indicators**: Announce status-notice lines in room chat ("bob is now away", "bob is an admin"; whole line only, ordinary chat is ignored). Config-gated: `status_indicator_enabled`. (see `docs/camfrog-re/14-png-assets.md`)
6. **Camfrog Upgrade/Payment Alerts**: Detect upgrade/payment-required status text and alert admin. Config-gated: `status_alert_enabled`. (see `docs/camfrog-re/07-upgrade-logic.md`, `09-payment.md`)
7. **Camfrog Name Color Tracking**: Read nickname color (`color: #RRGGBB`) from incoming chat HTML for GUI preview (read-only; AutoDJ cannot set name color). (see `docs/camfrog-re/15-name-color.md`)

### New in 0.2.8
1. **Font/Style Customization (GUI Preview Only)**: New `message_style` config section with font family, size, color, bold, italic, underline. Live preview in Settings tab. **Note**: Camfrog desktop client does NOT support rich text in outgoing messages — sent messages are always plain text via UIA. This feature is for the GUI preview panel only.
2. **Admin Greeting**: Greet admin on first message in session with configurable message and cooldown (default 1 hour).
3. **Delete History**: Admin command `!deletehistory <all|N>` to clear history or remove oldest N entries.
4. **IM-Only Play Commands**: `!play`, `!request`, `!req`, `!p`, `!เล่น`, `!ขอเพลง`, `!เล่นเพลง` now only work via private message (IM). Room users must DM the bot. Admins can still use in room.
5. **Autoplay Idle Timeout**: After 30 seconds (configurable) with no user requests, bot switches to autoplay pool. New `!play` immediately exits autoplay mode.
6. **New Thai Aliases**: `!ขอเพลง` (request song), `!เล่นเพลง` (play song).
7. **Auto-Reply**: Every 60 seconds (1 minute) from `ads-list.json` (configurable `auto_reply_interval`, min 60s).
8. **REA Reverse Engineering**: Documented Camfrog font logic (GDI imports, chat/IM font settings, HTML rendering for display only).
9. **Music Mute/Unmute**: Admin commands `!mute` / `!unmute` silence / restore AutoDJ's music by setting the player volume to 0 and back. They do not mute the Camfrog microphone (config-gated: `admin_mute_mic`, `admin_unmute_mic`; the key names are kept for compatibility).
10. **Block/Unblock Bot**: Admin commands `!blockbot` / `!unblockbot` to block/unblock bots (config-gated: `admin_block_bot`, `admin_unblock_bot`).
11. **Kick/Ban/Unban User**: Admin commands `!kick` / `!ban` / `!unban` (config-gated: `admin_kick_user`, `admin_ban_user`, `admin_unban_user`).
12. **Punish User/Bot**: Admin commands `!punish` / `!punishbot` (config-gated: `admin_punish_user`, `admin_punish_bot`).
13. **Delete Message**: Admin command `!delete <msg id>` to delete a message by ID (config-gated: `admin_delete_message_enabled`).
14. **Welcome Message**: Welcome message feature with configurable text (config-gated: `welcome_message_enabled`).
15. **Camfrog Gift Detection**: Detect virtual-gift messages in room chat (`GIFT_RECEIVED`, `room_gift_message`, `camfrog://gift`, etc.) and announce them. Config-gated: `gift_announce_enabled`. (see `docs/camfrog-re/08-feature-gift.md`)
16. **Camfrog Avatar Change Detection**: Detect avatar change messages in room chat (`updateAvatarMessage`) and announce them. Config-gated: `avatar_change_enabled`. (see `docs/camfrog-re/16-user-icon-avatar.md`)
17. **Camfrog Status Indicators**: Announce status-notice lines in room chat ("bob is now away", "bob is an admin"; whole line only, ordinary chat is ignored). Config-gated: `status_indicator_enabled`. (see `docs/camfrog-re/14-png-assets.md`)
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
Everyone: `np` (เพลงนี้; replies with live progress, e.g. `(1:05/3:20)`), `next` (ถัดไป), `queue` (คิว), `history` (ประวัติ), `voteskip` (โหวตข้าม), `remove <n>` (ลบ), `help` (ช่วยเหลือ), `mute` (ปิดไมค์), `unmute` (เปิดไมค์), `welcome` (ต้อนรับ).
Requester/admin: `skip` (ข้าม).
Admin: `pause` (หยุดชั่วคราว), `resume` (เล่นต่อ), `vol` (เสียง), `shuffle` (สุ่ม), `repeat` (วนซ้ำ), `clear` (ล้างคิว), `load` (โหลด), `say` (พูด), `speak` (ออกเสียง), `block <nick>` (บล็อก) / `unblock <nick>` (เลิกบล็อก), `blockbot <nick>` (บล็อกบอท) / `unblockbot <nick>` (เลิกบล็อกบอท), `kick <nick>` (เตะ), `ban <nick>` (แบน), `unban <nick>` (เลิกแบน), `punish <nick>` (ลงโทษ), `punishbot <nick>` (ลงโทษบอท), `deletehistory <all|N>` (ลบประวัติ), `delete <msg id>` (ลบข้อความ), `welcome <text>` (ต้อนรับ), `ai on|off|status|model <id>|prompt <text>` (เอไอ; everyone may use `ai ask <question>` / `เอไอ ถาม`), `update` / `update apply` (อัปเดต): a blocked nick's commands are ignored silently (admins cannot be blocked; also settable as `blocked_users` in config).

**"What song is this?"** Room lines containing `np_question_keywords` (e.g. "เพลงอะไร", "ชื่อเพลง", "what song") get the `!np` reply without a command; room-wide cooldown `np_question_cooldown` (default 20 s); disable with `np_question_reply = false` or in Settings. `msg_now` / `msg_next` templates accept `{title} {duration} {requester} {elapsed} {remaining} {eta}`. AI replies never answer private IMs; auto-update is off by default and only keeps SHA-256-verified downloads; webhook requests need `X-Timestamp` + `X-Signature` and a `webhook_secret` of at least 16 chars (see `docs/admin-manual.en.md`).

**Play commands (`!play`, `!request`, `!req`, `!p`, `!เล่น`, `!ขอเพลง`, `!เล่นเพลง`) now only work via IM (private message).** Room users must DM the bot. Admins can still use in room.

Non-admins: YouTube links only, 1 track, `max_duration`, no live, `max_requests_per_user`, and a song already queued or playing is refused. Name requests search `music_dirs` first, then YouTube.

**Requests always come first:** `!play` requests play in the order they arrive (first come, first served), ahead of the autoplay pool; a request also cuts an autoplay or startup song short. When the queue runs out and nobody requests anything for `autoplay_idle_timeout` (default 30 seconds, counted from when the last requested song finished), AutoDJ plays the default song (`default_track`) or, without one, the autoplay pool. A new `!play` request immediately exits autoplay mode.

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
- Close `AutoDJ.exe` before building (it cannot be rebuilt or signed while running). `autodj/__init__.py` must contain only `__version__`.

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
**Uninstall:** Start Menu → AutoDJ → Uninstall, or run `uninstall.ps1` in the project folder.

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


