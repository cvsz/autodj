# AutoDJ Admin Manual — English

**Version:** 0.3.10  
**Audience:** Room administrators and bot operators  
**Language:** English

---

## Overview

This manual covers administrative features, configuration, and operational procedures for AutoDJ. Regular users should refer to the [User Manual](user-manual.en.md).

---

## Admin Commands

### Playback Control

| Command | Aliases | Description | Example |
|---------|---------|-------------|---------|
| `pause` | `หยุดชั่วคราว` | Pause current playback | `!pause` |
| `resume` | `unpause`, `เล่นต่อ` | Resume paused playback | `!resume` |
| `skip` | `ข้าม` | Skip current track (any track) | `!skip` |
| `vol` | `volume`, `เสียง` | Set volume 0-100, or show current | `!vol 80` / `!vol` |

### Queue Management

| Command | Aliases | Description | Example |
|---------|---------|-------------|---------|
| `clear` | `ล้างคิว` | Clear all requests from queue | `!clear` |
| `shuffle` | `สุ่ม` | Toggle shuffle mode | `!shuffle on` / `!shuffle off` |
| `repeat` | `วนซ้ำ` | Set repeat mode | `!repeat one` / `!repeat off` |
| `remove` | `rm`, `ลบ` | Remove any request by position | `!remove 3` |

### History Management

| Command | Aliases | Description | Example |
|---------|---------|-------------|---------|
| `history` | `recent`, `ประวัติ` | Show recent played tracks | `!history` |
| `clearhistory` | `ล้างประวัติ` | Clear all history | `!clearhistory` |
| `deletehistory` | `delhistory`, `ลบประวัติ` | Delete last N or all history | `!deletehistory 10` / `!deletehistory all` |
| `last` | `requested`, `ขอล่าสุด` | Show last 5 user requests | `!last` |

### Music Loading

| Command | Aliases | Description | Example |
|---------|---------|-------------|---------|
| `load` | `โหลด` | Load playlist/folder/file to autoplay pool | `!load <source>` |

**Load Sources:**
- YouTube playlist URL: `!load https://youtube.com/playlist?list=PL...`
- Local folder: `!load D:\Music\Pop`
- Local file: `!load song.mp3`
- YouTube search (autoplay): `!load ytsearch20:thai pop`

### Communication

| Command | Aliases | Description | Example |
|---------|---------|-------------|---------|
| `say` | `พูด` | Send message to room chat | `!say Hello everyone!` |
| `speak` | `tts`, `ออกเสียง` | Text-to-speech (music ducks) | `!speak Welcome!` |

### User Management

| Command | Aliases | Description | Example |
|---------|---------|-------------|---------|
| `block` | `บล็อก` | Block user from commands | `!block spammer` |
| `unblock` | `เลิกบล็อก` | Unblock user | `!unblock spammer` |

### AI & Updates

| Command | Aliases | Description | Example |
|---------|---------|-------------|---------|
| `ai` | `เอไอ` | `on` / `off` / `status` / `model <id>` / `prompt <text>` — takes effect immediately (runtime only; edit config.toml to persist). `!ai` alone shows the status; `!ai help` sends the full command list to you by IM | `!ai status` / `!ai help` |
| `update` | `อัปเดต` | Check GitHub for a strictly newer release; `apply` downloads it (SHA-256 verified) and stages `AutoDJ.next.exe` + `autodj_update.bat` | `!update` / `!update apply` |

### Information

| Command | Aliases | Description | Example |
|---------|---------|-------------|---------|
| `help` | `commands`, `ช่วยเหลือ` | Show all commands (includes admin) | `!help` |
| `np` | `nowplaying`, `เพลงนี้` | Current track + live progress `(elapsed/total)` | `!np` |
| `next` | `upnext`, `ถัดไป` | Next track | `!next` |
| `queue` | `q`, `คิว` | Full queue | `!queue` |
| `voteskip` | `vs`, `โหวตข้าม` | Vote skip (admin can also use) | `!voteskip` |
| `aplay` | `addm` | Request a song via IM | `/aplay <song or YouTube link>` |
| `nowp` | `เพลงนี้` | Show current song (alias of np) | `/nowp` |
| `skipp` | `ข้ามเพลง` | Skip current song (alias of skip) | `/skipp` |
| `lastp` | `ขอล่าสุด` | Show last played song (alias of last) | `/lastp` |
| `hbdp` | `hbdm` | Birthday wish + play birthday song | `/hbdp <name>` |
| `topp` | `topm` | Top requested songs today/week | `/topp` or `/topp week` |
| `favp` | `favm` | Save current song to favorites | `/favp` |
| `myfavp` | `myfavm` | View your favorites | `/myfavp` |
| `hadj` | `helpm`, `คู่มือ` | Full command guide (both pages) | `/hadj` |

---

## Configuration (config.toml)

### Required Admin Setup

```toml
# === ADMIN CONFIGURATION ===
# Add your Camfrog nickname(s) here (case-insensitive)
admins = ["YourNick", "BackupAdmin"]

# Bot's own nickname in the room (for echo detection)
bot_nick = "AutoDJ"            # shipped default; set the nick the bot really chats as

# Command prefix
prefix = "!"
```

### Room & Connection

```toml
# Camfrog room window detection
window_title_re = ".*"              # Room window title regex
process_re = "(?i)camfrog"          # Process name filter
window_exclude_re = ""              # Drop matching titles when several windows match
window_index = 0                    # Pick the Nth remaining match
auto_discover = true                # Auto-detect room window at startup

# Chat adapter: "uia" (Windows UI Automation) | "logtail" | "console"
chat_reader = "uia"
chat_sender = "uia"

# UIA-specific (auto-filled by --discover)
view_kind = "auto"                  # auto | web | text
send_mode = "auto"                  # background | foreground | auto
send_verify = true                  # auto: check the line really appeared in the room
web_strict_body = true              # web view: drop plain text right after message body
web_view_title = "wb-log-room-data" # substring of the chat-history pane title
web_input_title = "wb-edit-data"    # substring of the message-box pane title
view_type = "Document"              # (filled in by auto_discover)
view_index = 0
input_type = "Edit"
input_index = -1
line_regex = '^(?:\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*)?(?P<user>[^:\s][^:]{0,30}):\s(?P<text>.+)$'
log_path = ""                       # also write the log to this file (rotating, 1 MB x 3)
log_encoding = "utf-8"              # log file encoding
```

### Audio Settings

```toml
# mpv player path (required)
mpv_path = "mpv/mpv.exe"            # or full path: "C:/mpv/mpv.exe"

# yt-dlp path (auto-detected if empty)
ytdlp_path = ""                     # "" = auto: next to mpv or on PATH; or "C:/mpv/yt-dlp.exe"

# YouTube authentication (optional)
youtube_cookies_file = ""           # path to Netscape cookies.txt for yt-dlp
youtube_cookies_browser = ""        # browser name for --cookies-from-browser (e.g. chrome, edge, firefox)
youtube_ca_bundle = ""              # path to custom CA bundle PEM file for yt-dlp certificate verification

# Audio output device (from: mpv --audio-device=help)
audio_device = "auto"               # "auto" = system default; or wasapi/{GUID} for virtual cable

# Audio effects
audio_fade = true                   # enable audio volume fade-in and fade-out
audio_fade_in_sec = 1.2             # fade-in duration in seconds
audio_fade_out_sec = 1.5            # fade-out duration on skip/stop in seconds
audio_normalize = false             # enable dynamic audio loudness normalization (dynaudnorm)

# Default volume (0-100)
volume = 100
```

### Music Library

```toml
# Local music folders (users can request by name)
music_dirs = ["D:/Music", "E:/Music2"]

# Additional autoplay sources (YouTube playlists, folders, files)
autoplay_sources = [
    "https://www.youtube.com/playlist?list=PL...",
    "D:/Music/Autoplay"
]

# Shuffle autoplay pool (shuffle bag: no repeat until every song has played; the pool loops forever)
shuffle = true
```

### Limits & Protection

```toml
# YouTube domains allowed for requests
allowed_hosts = ["youtube.com", "youtu.be", "music.youtube.com"]

# Per-user limits
max_requests_per_user = 3      # Max simultaneous requests in queue
user_request_limit = 5         # Max requests per sliding window
rate_limit_window = 300.0      # Sliding window (seconds)

# Queue limits
max_queue = 50                 # Total queue size
max_duration = 900             # Max track length (seconds) for non-admins

# Vote skip
voteskip_threshold = 3         # Votes needed to skip
voteskip_dynamic = false       # Dynamic threshold based on participants
voteskip_dynamic_pct = 30      # Percentage for dynamic mode
voteskip_cooldown = 10.0       # Seconds between voteskips from same user

# Cooldown & flood control
cooldown = 3.0                 # Seconds between commands per user
send_interval = 1.5            # Seconds between chat messages
max_msg_len = 200              # Max message length
```

### Announcements & "What song?" Replies

```toml
announce_next = true                # announce the up-next track in chat

# Answer room lines like "เพลงอะไร" / "what song" without a command (same text as !np)
np_question_reply = true
np_question_keywords = ["เพลงอะไร", "เพลงไร", "เพลงชื่อ", "ชื่อเพลง", "เพลงนี้ชื่อ", "what song", "whats playing", "what's playing", "song name"]
np_question_cooldown = 20.0         # room-wide seconds between auto-answers (0-3600)

# Templates ("" = built-in text for `lang`)
msg_now = ""
msg_next = ""                       # e.g. "Up next in {eta}: {title} requested by {requester}"
```

- Template fields: `{title}`, `{duration}`, `{requester}`, plus `{elapsed}` / `{remaining}` (progress of the current song) and `{eta}` (in `msg_next`: time until that song starts). Unknown values render as `?`; a broken template falls back to the built-in text.
- `!np` / `!nowplaying` / `!เพลงนี้` reply with the now-playing text plus `(elapsed/total)`, e.g. `กำลังเล่น: X [3:20] - ขอโดย bob (1:05/3:20)`.
- Keywords match as case-insensitive substrings; lines starting with the command prefix are ignored. The toggle is also in the GUI Settings dialog.

### Autoplay & Idle Behavior

```toml
# Seconds of no user requests before switching to autoplay
autoplay_idle_timeout = 30.0       # Min 30s

# Playlist persistence
playlist_file = "playlist.json"    # User requests saved here (deduplicated)
playlist_dir = ""         # Folder of .json playlist files (auto-loaded at startup); "" = disabled
search_limit = 1                   # YouTube search results per non-admin !play (1 = first match only; max 50)

# mpv timeout (0 = never timeout)
mpv_timeout = 30                   # seconds to wait for one mpv track before treating it as hung
```

- The autoplay pool loops forever; with `shuffle = true` no song repeats until every song in the pool has played.
- The "Up next" announcement always names the track that actually plays next.
- "Now playing" is announced once per track, also with `!repeat one`.

### Admin Greeting

```toml
# Greet an admin when they enter the room (they get this instead of the welcome)
admin_greeting_enabled = true
admin_greeting_message = "สวัสดีครับแอดมิน {admin} ยินดีต้อนรับกลับมา!"
admin_greeting_cooldown = 3600.0   # Seconds between greetings per admin (1 hour)
```

### IM Security (New in 0.3.0)

```toml
# Require user to be in room (seen in chat) to use IM commands
im_require_room_presence = true
```

### Auto-Reply (Scheduled Messages)

```toml
auto_reply_enabled = true
auto_reply_interval = 60.0        # seconds between auto-reply messages (min 60s)
auto_reply_file = "ads-list.json"  # JSON file with messages to rotate through
```

### TTS (Text-to-Speech)

```toml
tts_voice = ""                   # Substring of installed voice name
tts_rate = 170                   # Speech rate
tts_duck = 25                    # Music volume during TTS (0-100)
```

### Message Style (GUI Preview Only)

> **Note:** Camfrog desktop client does NOT support rich text in outgoing messages. This configuration is used ONLY for the FontEditor preview panel in the GUI. Sent messages are always plain text via UIA.

```toml
message_style = { 
    font_family = "Tahoma", 
    font_size = 14, 
    font_color = "#FF0000", 
    bold = true, 
    italic = false, 
    underline = false 
}
```

### Logging

```toml
log_file = ""                    # e.g. "autodj.log" (rotating 1MB x3)
log_path = ""                    # Custom log directory
log_encoding = "utf-8"

# JSON structured logging
log_json = false                 # enable JSON structured logging output
log_json_fields = [              # extra fields to include in JSON logs
  "request_id", "delivery_id", "user", "track_id", "generation",
  "attempt_id", "category", "stage", "state"
]
```

### Auto-Launch (Windows Only)

```toml
auto_launch = false              # Launch Camfrog and join room automatically
camfrog_exe = "%USERPROFILE%\\AppData\\Local\\Programs\\Camfrog Video Chat\\Camfrog Video Chat.exe"  # Path to Camfrog exe
client_title_re = ".*"           # Main client window title regex
room = ""                        # Room name to join
join_uri_template = "camfrog://room/{room}"  # URI template with {room} placeholder (URL-encoded)
launch_timeout = 60              # Seconds to wait for room window
```

### Blocked Users

```toml
blocked_users = []               # Nicks whose commands are ignored (admins cannot be blocked)
```

### IM Auto-Reply & Viewer

```toml
im_auto_reply_enabled = true       # enable auto-reply to private/instant messages
im_auto_reply_message = "Thanks for your message! I'm a bot and will respond when I can. Use !help for commands."
im_auto_reply_cooldown = 60.0      # seconds between auto-replies to the same user (avoid spam)
im_viewer_enabled = true           # show the IM / private message viewer tab in the GUI
im_require_room_presence = true    # only users seen in room chat can DM the bot; others get a private
                                   # reply from im_join_room_message (once per im_auto_reply_cooldown)
allow_play_in_room = true          # requests in room chat and by IM; false = IM only
```

### Camfrog RE Integrations (Gift / Avatar / Status / Alerts)

```toml
# Gift / virtual-gift announcement (detect gift messages in room chat)
gift_announce_enabled = true

# Avatar change announcement (detect avatar changes in room chat)
avatar_change_enabled = true

# Status indicator announcement (detect online/away/busy/invisible/admin/moderator/owner)
status_indicator_enabled = true

# Status alerts (detect upgrade/payment-required status text)
status_alert_enabled = true
```

### Welcome Message

```toml
welcome_message_enabled = true     # greet every user who enters the room
welcome_message_message = "ยินดีต้อนรับ {user} เข้าสู่ {room} สถานีเพลง อัตโนมัติ 24/7 ชั่วโมง"   # {user}, {room}
welcome_message_cooldown = 3600.0   # seconds between greetings for the same user (1 hour)
join_line_regex = '...'             # room "X has joined" notice, must contain (?P<user>...); "" = greet on first message
```

Arrival is detected from the room's join notice. The default pattern covers
`*** bob has joined the room`, `bob has entered the room` and `สมชาย เข้าสู่ห้อง`;
if your Camfrog client words it differently, copy one join line from the chat and adjust
`join_line_regex`. When no join notice is seen, users are greeted on their first message.
Each person gets one greeting per cooldown: admins get `admin_greeting_message`, everyone
else `welcome_message_message`. Plugins can react with `on_join(user)`.

### Mic / DJ Greeting

```toml
mic_greeting_enabled = true        # greet a user when the room shows they got the mic
mic_greeting_message = ""          # {user} = nick; "" = localized default ("{user} is now the DJ.")
mic_greeting_cooldown = 300.0      # seconds between mic greetings for the same user (0-86400)
```

Only a whole room line of the form `<nick> <mic phrase>` counts — `Seaza is now speaking`,
`Seaza has the mic`, `Seaza is the DJ`, `Seaza took the mic`, `Seaza กำลังรับไมค์`,
`Seaza กำลังพูด` — and only when the line's sender is that nick (or the line has no sender,
as for a system notice). Ordinary chat such as "who is the dj?" never triggers it, and one
user cannot get the bot to announce somebody else. Blocked users are skipped. All three
settings are also in the Settings dialog. Detection against a live Camfrog room is unverified:
if your client words the notice differently, the greeting will not fire.

### Admin Command Gating (Config-gated Features)

```toml
# Admin mic mute/unmute
admin_mute_mic = true
admin_unmute_mic = true

# Admin block/unblock user
admin_block_user = false
admin_unblock_user = false

# Admin block/unblock bot
admin_block_bot = true
admin_unblock_bot = true

# Admin kick/ban/unban user
admin_kick_user = true
admin_ban_user = true
admin_unban_user = true

# Admin punish user/bot
admin_punish_user = true
admin_punish_bot = true

# Admin delete message
admin_delete_message_enabled = true

# Mic mute state
mute_enabled = false
```

### JSON Structured Logging

```toml
log_json = false                       # enable JSON structured logging output
log_json_fields = [                    # extra fields to include in JSON logs
  "request_id", "delivery_id", "user", "track_id", "generation",
  "attempt_id", "category", "stage", "state"
]
```

### AI Chat Replies

```toml
ai_enabled = true                  # default on, but AI stays off until ai_api_key is set
ai_api_key = ""                    # NVIDIA key (nvapi-...) from https://build.nvidia.com/settings
ai_base_url = "https://integrate.api.nvidia.com/v1"   # any OpenAI-compatible endpoint; https required (http only for localhost/127.0.0.1/::1)
ai_model = "nvidia/llama-3.3-nemotron-super-49b-v1.5"   # NVIDIA API catalog model id
ai_system_prompt = "..."
ai_max_chars = 200                 # max characters in an AI reply
ai_user_cooldown = 30.0            # seconds between AI replies to the same user
```

- AI answers non-command room messages only. It **never** answers private IMs (the bot can only post to the public room, so that would leak the IM).
- URLs with embedded credentials are rejected. The per-user cooldown is enforced and also bounds API spend.
- `!ai on|off|status|model <id>|prompt <text>` (admin) take effect immediately; config edits apply on reload. `!ai` alone shows the status and `!ai help` sends the full command list by IM.
- Once `ai_api_key` is set, non-command room chat is sent to the configured AI endpoint (NVIDIA by default). Set `ai_enabled = false` if that is not wanted.

### Auto-Update

```toml
auto_update_enabled = false        # opt-in; when false there are no background requests to GitHub
auto_update_repo = "cvsz/autodj"
auto_update_check_interval = 21600.0   # seconds (min 300)
auto_update_asset = "AutoDJ.exe"
```

- Only a strictly newer version is offered; unparsable versions are never treated as newer.
- `!update` (admin) checks on demand; `!update apply` downloads the asset and keeps it only if its SHA-256 matches the GitHub asset `digest` or a `<asset>.sha256` / `SHA256SUMS` release asset. **Release maintainers must publish one of these**, otherwise the download is refused.
- The verified file is staged next to the exe with `autodj_update.bat`; run that script to swap and restart.

### Webhook / API Integration

```toml
webhook_enabled = false                # enable HTTP webhook server for external control
webhook_host = "127.0.0.1"             # host to bind webhook server (use 0.0.0.0 for external access)
webhook_port = 8080                    # port for webhook server
webhook_secret = ""                    # HMAC secret, >= 16 chars; empty/short = every request rejected with 503
webhook_rate_limit_per_ip = 60         # max requests per IP per minute
webhook_cors_origins = ["http://127.0.0.1:8080"]           # CORS allowed origins (e.g. ["https://example.com"]; default ["http://127.0.0.1:8080"])
```

Request signing (every request):

- `X-Timestamp`: unix time in seconds; must be within 300 s of the server clock.
- `X-Signature`: hex `HMAC-SHA256(webhook_secret, f"{timestamp}.{METHOD}.{path}." + raw_body)`.
- Each signature is accepted once (replays get 401). Missing/stale/invalid signature = 401; over `webhook_rate_limit_per_ip` = 429.

```python
import hashlib, hmac, time
ts = str(int(time.time()))
sig = hmac.new(secret.encode(), f"{ts}.POST./webhook/skip.".encode() + body, hashlib.sha256).hexdigest()
```

> **Note:** the webhook server code exists, but the engine does not start it at runtime yet; `webhook_enabled = true` currently has no effect.

### Config Hot Reload

```toml
config_hot_reload = false              # enable hot reload of config.toml (requires 'watchdog' extra: pip install -e .[hotreload])
```

### Plugin System

```toml
plugins = ["builtin.stats", "builtin.help"]  # list of plugin modules to load (e.g. "builtin.stats", "myplugin")
```

---

## GUI Features for Admins

### Header Buttons

- **EN/TH** — Switch language live
- **⚙️ Settings** — Open settings dialog (all config editable)
- **🔍 Discover room** — Run auto-discovery from GUI
- **✓ Check setup** — Run diagnostics from GUI

### Now Playing Card

- **Spinning record** — Visual playback indicator
- **Animated equalizer** — Decorative (not audio analysis)
- **Progress bar** — Click to seek
- **Volume slider** — Drag to change volume
- **ON AIR light** — Red when playing
- **Pause/Skip** — Round buttons
- **Voteskip progress** — Shows current votes/needed

### Tabs

1. **Queue** — Request list with Remove/Clear buttons
2. **History** — Recently played tracks
3. **Chat** — Room chat log with Say/Speak inputs

### Settings Dialog

Access via **⚙️ Settings** button. All config.toml settings editable with:
- Input validation (ranges, regex, choices)
- Atomic save with `.bak` backup
- Saving keeps keys the dialog does not show (`ai_*`, `auto_update_*`, `webhook_secret`, `voteskip_cooldown`, `log_json*`) instead of resetting them
- Toggle for answering "what song?" questions in the room (`np_question_reply`)
- Auto-relocation to `%APPDATA%\AutoDJ\` if install dir not writable
- Live language switch for labels

---

## Diagnostics & Maintenance

### Command Line Tools

```bash
# Full diagnostic check
AutoDJ.exe --check
# or
camfrog-autodj --check

# Auto-discover room window
AutoDJ.exe --discover

# List all windows (find Camfrog)
AutoDJ.exe --windows

# Dump window control tree
AutoDJ.exe --dump "Camfrog"

# Send test message to room
AutoDJ.exe --say "test message"

# Run with GUI
AutoDJ.exe --gui

# Run headless
AutoDJ.exe

# Console mode (type commands directly)
AutoDJ.exe --console --lang th
```

### Health Check Output

`--check` verifies:
- ✅ mpv executable found
- ✅ yt-dlp available (exe or Python module)
- ✅ JavaScript runtime (for yt-dlp)
- ✅ Music directories accessible
- ✅ Admin list not empty
- ✅ Config syntax valid
- ✅ Camfrog window detectable
- ✅ Python packages installed

### Log Files

- **Default:** Console output (stdout/stderr)
- **File:** Set `log_file = "autodj.log"` in config
- **Rotation:** 1 MB × 3 files
- **Location:** Relative paths resolve to `%APPDATA%\AutoDJ\`

### Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| "mpv not found" | mpv_path wrong or mpv not installed | Install mpv, set correct path |
| "yt-dlp not found" | yt-dlp missing | Put yt-dlp.exe next to mpv.exe or `pip install yt-dlp` |
| "YouTube lookup unavailable" | yt-dlp outdated or JS runtime missing | `yt-dlp -U`, install deno/node |
| "Config syntax error" | Invalid TOML | Check line with `^` marker, fix or copy example |
| "Could not play" | mpv error | Check log for mpv's error output |
| "GUI won't open" | Auto-discovery crash | Uses NullAdapter fallback; run `--check`/`--discover` from GUI |
| "Permission denied" config | Installed in Program Files | Auto-relocates to APPDATA |

---

## Building AutoDJ.exe (Windows)

### Prerequisites

- Windows 10/11
- Python 3.11+
- mpv installed
- yt-dlp.exe next to mpv.exe
- Visual Studio Build Tools (for PyInstaller)

### Build Steps

```powershell
# 1. Install dependencies
python -m pip install -e . pyinstaller

# 2. Build (self-signed cert created automatically)
.\build.ps1

# 3. Or with custom certificate
.\build.ps1 -Pfx cert.pfx -Password "secret"

# 4. Verify
dist\AutoDJ.exe --version
dist\AutoDJ.exe --check
```

### Build Options

| Option | Description |
|--------|-------------|
| `-Clean` | Clean build artifacts first |
| `-NoSign` | Skip code signing |
| `-Pfx` | Path to .pfx certificate |
| `-Password` | Certificate password |
| `-Thumbprint` | Cert thumbprint in user store |
| `-Subject` | Subject for self-signed cert |

---

## NSIS Installer (Windows)

### Build Installer

```powershell
make installer        # or: powershell -ExecutionPolicy Bypass -File scripts/build_installer.ps1
```

Build `dist\AutoDJ.exe` first (`make build`, or `make build-all` for exe + installer).
`scripts/build_installer.ps1` copies the current `config.example.toml` to `dist\config.toml`
(plus README, CHANGELOG and LICENSE) on every run, renders `installer.nsi` with the version
from `pyproject.toml`, then runs `makensis`. Running `makensis installer.nsi` by hand skips that
staging and can ship a stale config template. A developer's local `config.toml` is never packaged.

### Installer Features

- Per-user install to `%APPDATA%\AutoDJ` (no admin)
- Ships `config.toml` from `config.example.toml`; an existing `config.toml` is kept on upgrade
- Writes the absolute bundled `mpv_path` / `ytdlp_path` into `config.toml` (`AutoDJ.exe --write-install-paths`)
- Optional component: bundled mpv + yt-dlp in `%APPDATA%\AutoDJ\mpv` (never `%APPDATA%\mpv`, which is mpv's own config folder)
- Closes a running AutoDJ / mpv started from the install folder before upgrading or uninstalling
- Start Menu shortcuts (AutoDJ, Edit Config, Uninstall) and a Desktop shortcut
- Ships `install.ps1` for VB-CABLE and other prerequisites (VB-CABLE is not bundled)
- Uninstaller keeps `config.toml`, playlists, logs and other user data

---

## Security Considerations

### Nickname-Based Authorization

> ⚠️ **WARNING:** Admin authorization uses Camfrog display nicknames, which are **spoofable**. Any user can change their nick to match an admin and gain admin privileges.

**Mitigations:**
- Use unique, hard-to-guess admin nicks
- Keep `admins` list minimal
- Monitor logs for suspicious admin activity
- Consider `im_require_room_presence = true` (default)

### Fail-Closed Behavior

- Empty `admins` list = **no admin access** via nickname
- Local console (`--console`) always has admin rights
- Blocked users get **silent ignore** (no error messages)

### Configuration Safety

- Atomic writes (temp file + `os.replace`)
- `.bak` backup on every save
- Validation before write (ranges, regex, choices)
- Auto-relocation if config not writable

---

## Upgrading

### From 0.2.x

1. **Backup** your `config.toml` and `playlist.json`
2. **Pull latest** code
3. **Run** `python -m pip install -e . --upgrade`
4. **Check** `AutoDJ.exe --check`
5. **Verify** config migration (auto-runs on startup)

### Config Migration

AutoDJ automatically migrates:
- Placeholder paths (`REPLACE_ME`) → defaults
- Old keys → new structure
- Creates `config.toml.bak` before changes

---

## File Locations

| File | Default Location | Description |
|------|------------------|-------------|
| `config.toml` | `%APPDATA%\AutoDJ\` | Main configuration |
| `playlist.json` | Same as config | Persisted user requests |
| `ads-list.json` | Same as config | Auto-reply messages |
| `autodj.log` | Same as config | Rotating log file |
| `config.toml.bak` | Same as config | Backup from last save |

---

## Advanced Features

### YouTube Authentication

```toml
youtube_cookies_file = ""        # Netscape cookies.txt for yt-dlp
youtube_cookies_browser = ""     # e.g. "chrome", "firefox", "edge"
youtube_ca_bundle = ""           # Custom CA bundle for cert verification
```

### Audio Engineering

```toml
audio_fade = true                # Enable fade in/out
audio_fade_in_sec = 1.2          # Fade in duration
audio_fade_out_sec = 1.5         # Fade out duration
audio_normalize = false          # Dynamic loudness normalization (dynaudnorm)
```

### Dynamic Vote Skip

```toml
voteskip_dynamic = false
voteskip_dynamic_pct = 30        # % of participants needed
```

### Per-User Rate Limiting

```toml
user_request_limit = 5           # Max requests
rate_limit_window = 300.0        # Sliding window (seconds)
```

---

## Troubleshooting Checklist

- [ ] Run `AutoDJ.exe --check` — all green?
- [ ] `mpv --audio-device=help` — correct device in config?
- [ ] `yt-dlp -U` — latest version?
- [ ] Config TOML valid? (no syntax errors)
- [ ] Admin nick in `admins` list (case-insensitive)?
- [ ] Music directories exist and readable?
- [ ] Camfrog room window open?
- [ ] VB-Cable installed and set as mic in Camfrog?
- [ ] Audio device in config matches cable input?
- [ ] Log file writable? (check `log_file` path)

---

## Support

- **Logs:** Check `autodj.log` or console output
- **Debug:** Run with `-v` flag for verbose logging
- **GUI:** Use **Check setup** button for visual diagnostics
- **Config:** Use **Settings** dialog for safe editing
