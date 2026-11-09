# AutoDJ User Manual — English

**Version:** 0.2.8  
**Audience:** Room participants (non-admin users)  
**Language:** English

---

## Quick Start

1. **Join the Camfrog room** where AutoDJ is running
2. **Send a private message (IM/DM) to the bot** with your song request
3. **Use commands** like `play <song name>` or `play <YouTube URL>`
4. **Enjoy the music!**

> **Important:** Song requests ONLY work via Private Message (IM). Room chat commands for playing songs are restricted to admins.

---

## How to Request a Song

### Via Private Message (IM) — **Required for regular users**

Send a direct message to the bot:

```
play never gonna give you up
play https://www.youtube.com/watch?v=dQw4w9WgXcQ
play despacito
request Bohemian Rhapsody
```

### Supported Request Formats

| Format | Example | Description |
|--------|---------|-------------|
| **Song name** | `play never gonna give you up` | Searches YouTube and plays first result |
| **YouTube URL** | `play https://youtu.be/dQw4w9WgXcQ` | Plays specific video |
| **YouTube Music** | `play https://music.youtube.com/watch?v=...` | Plays from YouTube Music |
| **Local file** | `play my_song.mp3` | Searches your music library folders |

> **No prefix needed in IM!** Just type the command directly.

---

## Available Commands (All Users)

| Command | Aliases | Description |
|---------|---------|-------------|
| `play` | `request`, `req`, `p`, `เล่น`, `ขอเพลง`, `เล่นเพลง` | Request a song |
| `np` | `nowplaying`, `เพลงนี้` | Show currently playing song |
| `next` | `upnext`, `ถัดไป` | Show next song in queue |
| `queue` | `q`, `คิว` | Show request queue (first 5) |
| `history` | `recent`, `ประวัติ` | Show recently played songs |
| `voteskip` | `vs`, `โหวตข้าม` | Vote to skip current song |
| `remove` | `rm`, `ลบ` | Remove your own request by queue number |
| `last` | `requested`, `ขอล่าสุด` | Show last 5 requested songs |
| `help` | `commands`, `ช่วยเหลือ` | Show all commands |

### Examples

```
play despacito
np
next
queue
history
voteskip
remove 2
last
help
```

---

## Understanding the Queue

- **Your requests** appear in the queue with your name
- **Position 1** = playing next (after current song)
- **Maximum 3 requests** in queue per user (configurable)
- **Maximum 50 total** requests in queue (configurable)
- **Duplicate protection** — same song won't be queued twice
- **Max song length:** 15 minutes (900 seconds) for non-admins

---

## Vote Skip

- Type `voteskip` to vote for skipping the current song
- **Default threshold:** 3 votes needed (configurable)
- **Dynamic threshold** (optional): Based on room participant count
- Only works when a song is playing

---

## Removing Your Request

```
remove 2
```

- Removes the request at position **2** in the queue
- You can only remove **your own** requests
- Admins can remove any request

---

## History & Recent Requests

- `history` — Shows last 5 played songs
- `last` — Shows last 5 songs requested by users (saved to playlist.json)

---

## Rate Limits & Cooldowns

| Limit | Default | Description |
|-------|---------|-------------|
| **Cooldown** | 3 seconds | Wait between commands |
| **Max requests in queue** | 3 per user | Your simultaneous requests |
| **Request rate limit** | 5 per 5 minutes | Sliding window |
| **Max song duration** | 15 minutes | Non-admin requests |

> Exceeding limits will show an error message. Wait and try again.

---

## Autoplay Mode

- When **no requests for 30 seconds**, bot switches to autoplay
- Autoplay picks random songs from: your music folders, configured sources, playlist.json
- **Any new request** immediately exits autoplay mode
- Announcement: *"No user requests for 30 seconds. Switching to autoplay mode."*

---

## Blocked Users

- Admins can block users: `!block <nick>`
- Blocked users' commands are **silently ignored**
- Admins cannot be blocked
- Use `!unblock <nick>` to unblock

---

## Language Support

- **English** (`lang = "en"`) — Default
- **Thai** (`lang = "th"`) — Full Thai translation
- Switch live in GUI header (EN/TH buttons)
- All commands work in both languages

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "YouTube lookup unavailable" | Bot needs yt-dlp. Ask admin to run `AutoDJ.exe --check` |
| "Could not play" | Song may be unavailable, region-locked, or mpv issue |
| "Max requests reached" | Wait for your songs to play or remove old requests |
| "Already queued" | Song is already in queue or playing |
| "Live streams not allowed" | Non-admins cannot request live streams |
| "Too long" | Song exceeds 15-minute limit |
| "Not in room" | Join the Camfrog room and chat once before using IM |

---

## Tips

1. **Use IM for requests** — Room chat play commands are admin-only
2. **Be specific** — "play despacito luis fonsi" works better than just "despacito"
3. **Check queue first** — Use `queue` to see your position
4. **Vote skip** — If you don't like current song, rally votes!
5. **History persists** — `last` command shows requests across restarts

---

## Privacy & Security

- **Nickname-based auth** — Admins identified by nickname (spoofable)
- **No persistent storage** of private messages
- **Local music library** only accessible via configured folders
- **Config file** stores settings only, no personal data

---

## Getting Help

- Type `help` in IM for command list
- Ask room admins for assistance
- Check bot's log for detailed errors (admin only)
- Run `AutoDJ.exe --check` for diagnostics (admin only)