# AutoDJ Admin Manual — English

**Version:** 0.2.8  
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

### Information

| Command | Aliases | Description | Example |
|---------|---------|-------------|---------|
| `help` | `commands`, `ช่วยเหลือ` | Show all commands (includes admin) | `!help` |
| `np` | `nowplaying`, `เพลงนี้` | Current track info | `!np` |
| `next` | `upnext`, `ถัดไป` | Next track | `!next` |
| `queue` | `q`, `คิว` | Full queue | `!queue` |
| `voteskip` | `vs`, `โหวตข้าม` | Vote skip (admin can also use) | `!voteskip` |

---

## Configuration (config.toml)

### Required Admin Setup

```toml
# === ADMIN CONFIGURATION ===
# Add your Camfrog nickname(s) here (case-insensitive)
admins = ["YourNick", "BackupAdmin"]

# Bot's own nickname in the room (for echo detection)
bot_nick = "AutoDJ"

# Command prefix
prefix = "!"
```

### Room & Connection

```toml
# Camfrog room window detection
window_title_re = ".*"          # Room window title regex
process_re = "(?i)camfrog"      # Process name filter
auto_discover = true            # Auto-detect room window at startup

# Chat adapter: "uia" (Windows UI Automation) | "logtail" | "console"
chat_reader = "uia"
chat_sender = "uia"

# UIA-specific (auto-filled by --discover)
view_kind = "auto"
view_type = "Document"
view_index = 0
input_type = "Edit"
input_index = -1
line_regex = '^(?:\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*)?(?P<user>[^:\s][^:]{0,30}):\s(?P<text>.+)$'
```

### Audio Settings

```toml
# mpv player path (required)
mpv_path = "mpv"                    # or full path: "C:/mpv/mpv.exe"

# yt-dlp path (auto-detected if empty)
ytdlp_path = ""                     # or "C:/mpv/yt-dlp.exe"

# Audio output device (from: mpv --audio-device=help)
audio_device = ""                   # e.g. "wasapi/{guid}" for virtual cable

# Default volume (0-100)
volume = 70
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

# Shuffle autoplay pool
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

# Cooldown & flood control
cooldown = 3.0                 # Seconds between commands per user
send_interval = 1.5            # Seconds between chat messages
max_msg_len = 180              # Max message length
```

### Autoplay & Idle Behavior (New in 0.2.8)

```toml
# Seconds of no user requests before switching to autoplay
autoplay_idle_timeout = 30.0   # Min 60s if auto_reply_enabled

# Playlist persistence
playlist_file = "playlist.json"    # User requests saved here
playlist_dir = ""                  # Folder of .json playlist files
search_limit = 1                   # YouTube search results per request

# mpv timeout (0 = never timeout)
mpv_timeout = 30
```

### Admin Greeting (New in 0.2.8)

```toml
# Greet admin on first message in session
admin_greeting_enabled = false
admin_greeting_message = "Welcome back admin {admin}!"
admin_greeting_cooldown = 3600.0   # Seconds between greetings per admin
```

### IM Security (New in 0.2.8)

```toml
# Require user to be in room (seen in chat) to use IM commands
im_require_room_presence = true
```

### Auto-Reply (Scheduled Messages)

```toml
auto_reply_enabled = false
auto_reply_interval = 300.0      # Min 60 seconds
auto_reply_file = "ads-list.json"  # JSON file with messages
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
    font_family = "Consolas", 
    font_size = 14, 
    font_color = "#FF0000", 
    bold = false, 
    italic = false, 
    underline = false 
}
```

### Logging

```toml
log_file = ""                    # e.g. "autodj.log" (rotating 1MB x3)
log_path = ""                    # Custom log directory
log_encoding = "utf-8"
```

### Auto-Launch (Windows Only)

```toml
auto_launch = false              # Launch Camfrog and join room automatically
camfrog_exe = ""                 # Path to Camfrog executable
client_title_re = ".*"           # Main client window title regex
room = ""                        # Room name to join
join_uri_template = ""           # URI template with {room} placeholder
launch_timeout = 60              # Seconds to wait for room window
```

### Blocked Users

```toml
blocked_users = []               # Nicks whose commands are ignored
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
- Auto-relocation to `%APPDATA%\CamfrogAutoDJ\` if install dir not writable
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
- **Location:** Relative paths resolve to `%APPDATA%\CamfrogAutoDJ\`

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
# Requires NSIS 3.0+ with MUI2
makensis installer.nsi
```

### Installer Features

- Per-user install to `%APPDATA%\CamfrogAutoDJ` (no admin)
- Installs Python, mpv, yt-dlp, VB-Cable via winget
- Creates Desktop/Start Menu shortcuts
- Generates config.toml interactively
- Optional auto-start on login
- Runs `AutoDJ.exe --check` verification
- Uninstaller included

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
| `config.toml` | `%APPDATA%\CamfrogAutoDJ\` | Main configuration |
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