# AutoDJ Commands Reference — English

**Version:** 0.3.0  
**Prefix:** `!` (configurable via `prefix` in config.toml)  
**Language:** English (`lang = "en"`)

---

## Table of Contents

1. [General Commands](#general-commands) — Available to everyone
2. [Requester/Admin Commands](#requesteradmin-commands) — Available to requester and admins
3. [Admin Commands](#admin-commands) — Available to admins only
4. [IM (Private Message) Commands](#im-private-message-commands) — Special behavior in DMs
5. [Command Aliases](#command-aliases)

---

## General Commands

| Command | Aliases | Description | Usage |
|---------|---------|-------------|-------|
| `help` | `commands` | Show all available commands | `!help` |
| `play` | `request`, `req`, `p` | Request a song by YouTube URL, search term, or local file name | `!play <url\|name>` |
| `np` | `nowplaying` | Show currently playing track | `!np` |
| `next` | `upnext` | Show next track in queue | `!next` |
| `queue` | `q` | Show current request queue (first 5) | `!queue` |
| `history` | `recent` | Show recently played tracks (last 5) | `!history` |
| `voteskip` | `vs` | Vote to skip current track | `!voteskip` |
| `remove` | `rm` | Remove your own request from queue by position | `!remove <n>` |
| `last` | `requested` | Show last 5 requested tracks (from playlist.json) | `!last` |
| `aplay` | `addm` | Request a song via IM (alias of play); supports `/aplay fav <n>` | `/aplay <song or YouTube link>` |
| `nowp` | `เพลงนี้` | Show current song (alias of np) | `/nowp` |
| `skipp` | `ข้ามเพลง` | Skip current song (alias of skip) | `/skipp` |
| `lastp` | `ขอล่าสุด` | Show last played song (alias of last) | `/lastp` |
| `hbdp` | `hbdm` | Birthday wish + play birthday song | `/hbdp <name>` |
| `topp` | `topm` | Top requested songs today/week | `/topp` or `/topp week` |
| `favp` | `favm` | Save current song to favorites | `/favp` |
| `myfavp` | `myfavm` | View your favorites | `/myfavp` |
| `hadj` | `helpm`, `คู่มือ` | Full command guide (both pages) | `/hadj` |

### Examples

```
!play https://www.youtube.com/watch?v=dQw4w9WgXcQ
!play never gonna give you up
!play despacito
!np
!next
!queue
!history
!voteskip
!remove 2
!last
```

---

## Requester/Admin Commands

| Command | Aliases | Description | Usage |
|---------|---------|-------------|-------|
| `skip` | — | Skip current track (requester or admin only) | `!skip` |

### Examples

```
!skip
```

---

## Admin Commands

| Command | Aliases | Description | Usage |
|---------|---------|-------------|-------|
| `pause` | — | Pause playback | `!pause` |
| `resume` | `unpause` | Resume playback | `!resume` |
| `vol` | `volume` | Set volume (0-100) or show current | `!vol [0-100]` |
| `shuffle` | — | Toggle shuffle mode | `!shuffle on\|off` |
| `repeat` | — | Set repeat mode | `!repeat off\|one` |
| `clear` | — | Clear all requests from queue | `!clear` |
| `clearhistory` | — | Clear playback history | `!clearhistory` |
| `deletehistory` | `delhistory` | Delete history entries | `!deletehistory all\|<N>` |
| `load` | — | Load playlist/folder/file into autoplay pool | `!load <source>` |
| `say` | — | Send message to room chat | `!say <text>` |
| `speak` | `tts` | Speak text via TTS (music ducks) | `!speak <text>` |
| `block` | — | Block a user from using commands | `!block <nick>` |
| `unblock` | — | Unblock a user | `!unblock <nick>` |

### Examples

```
!pause
!resume
!vol 80
!vol
!shuffle on
!shuffle off
!repeat one
!repeat off
!clear
!clearhistory
!deletehistory all
!deletehistory 10
!load https://www.youtube.com/playlist?list=PL...
!load D:\Music\Pop
!load song.mp3
!say Hello everyone!
!speak Welcome to the room
!block spammer123
!unblock spammer123
```

---

## IM Command Details

### /aplay (alias: /addm)

Request a song via IM. Works exactly like `!play` but without the `!` prefix.

**Examples:**
```
/aplay https://www.youtube.com/watch?v=dQw4w9WgXcQ
/aplay never gonna give you up
/aplay despacito
```

### /aplay fav <n>

Play a favorite song by its position number (1-based) from your favorites list. See `/favp` to view your favorites.

**Example:**
```
/aplay fav 1
/aplay fav 3
```

### /nowp (alias: /เพลงนี้)

Show the currently playing track and who requested it.

**Example:**
```
/nowp
```

### /skipp (alias: /ข้ามเพลง)

Skip the current track. Only the requester or a Main Owner can skip.

**Example:**
```
/skipp
```

### /lastp (alias: /ขอล่าสุด)

Show the last 5 played tracks.

**Example:**
```
/lastp
```

### /hbdp (alias: /hbdm)

Send a birthday wish to the room and play a birthday song.

**Example:**
```
/hbdp kris
/hbdp สมชาย
```

### /topp (alias: /topm)

Show the most requested songs today or this week.

**Examples:**
```
/topp
/topp week
```

### /favp (alias: /favm)

Save the currently playing song to your favorites.

**Example:**
```
/favp
```

### /myfavp (alias: /myfavm)

View your saved favorite songs.

**Example:**
```
/myfavp
```

### /hadj (alias: /helpm, /คู่มือ)

Show the full command guide (both pages). Sent as IM to the bot.

**Example:**
```
/hadj
```

---

## Command Aliases

### English Aliases

| Primary | Aliases |
|---------|---------|
| `help` | `commands` |
| `play` | `request`, `req`, `p` |
| `np` | `nowplaying` |
| `next` | `upnext` |
| `queue` | `q` |
| `history` | `recent` |
| `voteskip` | `vs` |
| `aplay` | `addm` |
| `nowp` | |
| `skipp` | |
| `lastp` | |
| `hbdp` | `hbdm` |
| `topp` | `topm` |
| `favp` | `favm` |
| `myfavp` | `myfavm` |
| `hadj` | `helpm` |
| `remove` | `rm` |
| `last` | `requested` |
| `resume` | `unpause` |
| `vol` | `volume` |
| `speak` | `tts` |
| `clearhistory` | — |
| `deletehistory` | `delhistory` |

### Thai Aliases

| Primary (English) | Thai Aliases |
|-------------------|--------------|
| `help` | `ช่วยเหลือ` |
| `play` | `เล่น`, `ขอเพลง`, `เล่นเพลง` |
| `np` | `เพลงนี้` |
| `next` | `ถัดไป` |
| `queue` | `คิว` |
| `history` | `ประวัติ` |
| `voteskip` | `โหวตข้าม` |
| `aplay` | `addm` |
| `nowp` | `เพลงนี้` |
| `skipp` | `ข้ามเพลง` |
| `lastp` | `ขอล่าสุด` |
| `hbdp` | `hbdm` |
| `topp` | `topm` |
| `favp` | `favm` |
| `myfavp` | `myfavm` |
| `hadj` | `helpm`, `คู่มือ` |
| `remove` | `ลบ` |
| `last` | `requested` |
| `skip` | `ข้าม` |
| `pause` | `หยุดชั่วคราว` |
| `resume` | `เล่นต่อ` |
| `vol` | `เสียง` |
| `shuffle` | `สุ่ม` |
| `repeat` | `วนซ้ำ` |
| `clear` | `ล้างคิว` |
| `clearhistory` | `ล้างประวัติ` |
| `deletehistory` | `ลบประวัติ` |
| `load` | `โหลด` |
| `say` | `พูด` |
| `speak` | `ออกเสียง` |
| `block` | `บล็อก` |
| `unblock` | `เลิกบล็อก` |

---

## Request Limits & Cooldowns

| Setting | Default | Description |
|---------|---------|-------------|
| `cooldown` | 3.0s | Minimum time between commands from same user |
| `max_requests_per_user` | 3 | Max requests in queue per user |
| `voteskip_threshold` | 3 | Votes needed to skip current track |
| `voteskip_cooldown` | 10.0s | Cooldown between voteskips from same user |
| `user_request_limit` | 5 | Max requests per user in sliding window |
| `rate_limit_window` | 300s | Sliding window for request limit |
| `max_duration` | 900s | Max track length for non-admin requests |
| `max_queue` | 50 | Max total requests in queue |

---

## Autoplay Behavior

- **Idle timeout:** 30 seconds (configurable: `autoplay_idle_timeout`)
- When no user requests for the timeout period, bot switches to autoplay pool
- New user request immediately exits autoplay mode
- Autoplay pool populated from: `music_dirs`, `autoplay_sources`, `playlist.json`

---

## Configuration Reference

Key settings in `config.toml`:

```toml
# Core
prefix = "!"
lang = "en"
bot_nick = "AutoDJ"
admins = ["admin_nick"]  # case-insensitive

# Chat
chat_reader = "uia"
chat_sender = "uia"
auto_discover = true

# Audio
mpv_path = "mpv"
ytdlp_path = ""
audio_device = ""
volume = 70

# Library
music_dirs = ["D:/Music"]
autoplay_sources = []
shuffle = true

# Limits
max_requests_per_user = 3
max_queue = 50
max_duration = 900
voteskip_threshold = 3
cooldown = 3.0
send_interval = 1.5

# Features
playlist_file = "playlist.json"
search_limit = 1
mpv_timeout = 30

# New in 0.2.8
autoplay_idle_timeout = 30.0
admin_greeting_enabled = false
admin_greeting_message = "Welcome back admin {admin}!"
admin_greeting_cooldown = 3600.0
im_require_room_presence = true

# Message style (GUI preview only - Camfrog sends plain text)
message_style = { font_family = "Consolas", font_size = 14, font_color = "#FF0000", bold = false, italic = false, underline = false }
```

---

## Notes

- **Case-insensitive:** Command names and admin nicks are case-insensitive
- **Thai/English:** Switch language live in GUI or set `lang = "th"` in config
- **IM Security:** Private message commands require user to be present in room chat
- **Rate limiting:** Sliding window prevents spam; cooldown prevents rapid commands
- **Duplicate protection:** Same song won't be queued twice
- **Admin fail-closed:** Empty admin list = no admin access via nickname