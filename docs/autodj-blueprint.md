# CamfrogAutoDJ — Complete Architecture Blueprint

**Version:** 0.3.0 (Enterprise Production Release)  
**Generated:** 2026-11-10  
**Repository:** https://github.com/cvsz/autodj  
**Total Source:** 10,085 lines across 32 modules  
**Test Coverage:** 375 tests + 3 subtests

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Module Catalog](#module-catalog)
3. [Core Data Models](#core-data-models)
4. [Exception Hierarchy](#exception-hierarchy)
5. [Configuration System](#configuration-system)
6. [Audio Engine](#audio-engine)
7. [Playback Queue & Playlist](#playback-queue--playlist)
8. [Command Router](#command-router)
9. [Chat Adapters](#chat-adapters)
10. [GUI Architecture](#gui-architecture)
11. [Camfrog Integration](#camfrog-integration)
12. [Library & YouTube](#library--youtube)
13. [Text & Rendering](#text--rendering)
14. [Security Model](#security-model)
15. [Concurrency & Threading](#concurrency--threading)
16. [Build & Deployment](#build--deployment)
17. [Missing / Future Enhancements](#missing--future-enhancements)

---

## System Overview

CamfrogAutoDJ is a **production-grade music bot** for Camfrog chat rooms. It provides:

- **YouTube + Local playback** via mpv/yt-dlp
- **Command system** with 30+ commands (`!play`, `!queue`, `!voteskip`, admin commands)
- **Auto-playlist** with persistent JSON storage
- **Now/Next announcements** with TTS support
- **Bilingual EN/TH** GUI and chat replies
- **Camfrog RE integrations**: gift detection, avatar changes, status indicators, upgrade/payment alerts
- **IM viewer** with auto-reply
- **Enterprise architecture**: circuit breakers, rate limiting, health checks, structured exceptions

### Key Architectural Principles

| Principle | Implementation |
|-----------|----------------|
| **Fail-closed config** | `ConfigError` on any invalid value; exact line + `^` marker |
| **One mpv per track** | No shared state; IPC for control |
| **GUI off main thread** | All playback in background; `tk.after(0, ...)` for cross-thread updates |
| **No symlinks** | `entry.is_symlink()` → `continue` (avoids cycles, reparse points) |
| **No `shell=True`** | All `subprocess` use argument lists |
| **Type safety** | `mypy --check-untyped-defs` = 0 errors |
| **Security boundaries** | Nickname auth documented as spoofable; IM requires room presence |

---

## Module Catalog

### Core Modules (32 files, 10,085 lines)

| Module | Lines | Purpose |
|--------|-------|---------|
| `engine.py` | 1,569 | Main orchestration: chat loop, playback loop, auto-reply, health checks |
| `gui.py` | 3,252 | Tkinter desktop window: studio look, animated EQ, tabbed queue/history/chat/IM |
| `commands.py` | 619 | Command router: 30+ commands, rate limiting, admin auth, TOCTOU protection |
| `config.py` | 394 | TOML config with validation, nested `MessageStyle`, atomic writes, auto-relocation |
| `player.py` | 310 | `MpvPlayer`: IPC, fade in/out, hang detection, graceful timeout |
| `library.py` | 317 | Local index, folder scanning, yt-dlp integration, metadata extraction |
| `playlist.py` | 200 | Persistent `playlist.json`: atomic writes, dedup by source, auto-load dir |
| `playqueue.py` | 101 | Thread-safe `PlayQueue`: requests first, then autoplay pool (looping) |
| `exceptions.py` | 334 | 20+ structured exceptions with codes (`config.error`, `player.hung`, etc.) |
| `models.py` | 35 | `Track` dataclass, `fmt_time`, `UserError` alias |
| `messages.py` | 421 | All user-facing strings EN/TH (300+ keys) |
| `discover.py` | 297 | Auto-discover Camfrog window/controls, write to config |
| `adapters/uia.py` | 365 | UI Automation chat adapter (web + text layouts) |
| `adapters/console.py` | 32 | Stdin/stdout chat for testing |
| `adapters/logtail.py` | 40 | Log file tailing adapter |
| `adapters/base.py` | 38 | Abstract `ChatAdapter`, `ChatMessage`, line parsing |
| `webchat.py` | 158 | Camfrog web view chat parsing (avatar = message boundary) |
| `winmsg.py` | 280 | Background window message sending (Win32) |
| `launcher.py` | 53 | Optional Camfrog client launch + room join |
| `tts.py` | 103 | pyttsx3 TTS with dedicated COM STA thread |
| `camfrog_font.py` | 270 | Windows registry font settings read/write |
| `migrate.py` | 228 | Config migration: placeholder detection, path discovery |
| `paths.py` | 60 | Executable resolution, env expansion, app dir detection |
| `renderer.py` | 111 | Message rendering (plain for send, rich for GUI preview) |
| `visuals.py` | 197 | Pure animation helpers (no tkinter) |
| `windows.py` | 122 | Camfrog window enumeration (pywinauto) |
| `clipkeys.py` | 26 | Clipboard keybindings for settings entries |
| `doctor.py` | 199 | Diagnostics: mpv, yt-dlp, folders, Camfrog window |
| `__main__.py` | 284 | CLI entry: `--gui`, `--console`, `--check`, `--discover`, config relocation |
| `__init__.py` | 128 | Version, package exports |

---

## Core Data Models

### `Track` (`models.py`)
```python
@dataclass
class Track:
    source: str                    # URL, ytsearchN:, or local path
    title: str
    duration: float | None = None  # seconds
    requester: str = "AutoDJ"
    added: str = ""                # ISO timestamp
    state: str = "QUEUED"          # QUEUED|RESOLVING|READY|PLAYING|COMPLETED|FAILED|CANCELLED
```

### `ChatMessage` (`adapters/base.py`)
```python
@dataclass
class ChatMessage:
    user: str
    text: str
    local: bool = False      # from local console = trusted admin
    is_im: bool = False      # instant/private message
```

### `MessageStyle` (`config.py`)
```python
@dataclass
class MessageStyle:
    font_family: str = "Consolas"
    font_size: int = 14
    font_color: str = "#FF0000"
    bold: bool = False
    italic: bool = False
    underline: bool = False
```

### `RenderedMessage` (`renderer.py`)
```python
@dataclass
class RenderedMessage:
    plain_text: str
    rich_text: Optional[str] = None      # Always None for sending
    preview_tags: Optional[dict] = None  # For tkinter Text widget preview
```

---

## Exception Hierarchy (`exceptions.py`)

```
AutoDJError (base)
├── ConfigError
│   └── ConfigValidationError
├── ChatError
│   ├── ChatReadError
│   └── ChatSendError
├── LibraryError
│   └── LibraryScanError
├── PlayerError
│   ├── PlayerCrashError
│   ├── PlayerHungError
│   └── PlayerNotAvailableError
├── QueueError
│   ├── QueueFullError
│   └── RequestRateLimitError
├── SecurityError
│   ├── BlockedUserError
│   └── UnauthorizedError
├── TTSError
│   └── TTSUnavailableError
└── YtdlpMissingError

# Each exception carries:
#   code: str        # Machine-readable (e.g., "config.invalid")
#   details: str     # Human-readable
#   context: dict    # Structured debugging context
```

---

## Configuration System (`config.py`)

### Loading Flow
1. `Config.load(path)` → reads TOML with `tomllib`
2. Syntax errors → `ConfigError` with line + `^` marker
3. Unknown keys → suggestion via `difflib`
4. Nested `message_style` → `MessageStyle.from_toml_dict()`
5. Validation order: type → choices → ranges → regexes → semantic
6. Atomic write: temp file + `os.replace()` + `.bak` backup
7. Auto-relocation: if not writable → `%APPDATA%\CamfrogAutoDJ\`

### Key Config Sections (56 validated keys)

| Section | Keys | Notes |
|---------|------|-------|
| **Identity** | `bot_nick`, `admins[]`, `prefix`, `lang` | `lang`: en/th |
| **Chat** | `chat_reader`, `chat_sender`, `window_title_re`, `process_re`, `send_mode`, `send_verify` | `uia`/`logtail`/`console` |
| **Window Discovery** | `auto_discover`, `view_kind`, `view_type`, `view_index`, `input_type`, `input_index` | Auto-filled by `--discover` |
| **Audio** | `mpv_path`, `ytdlp_path`, `audio_device`, `volume`, `mpv_timeout` | `audio_device="auto"` default |
| **Library** | `music_dirs[]`, `autoplay_sources[]`, `shuffle`, `allowed_hosts[]` | `playlist_dir="playlist"` |
| **Queue Limits** | `max_requests_per_user`, `max_queue`, `max_duration`, `voteskip_threshold`, `cooldown` | Dynamic voteskip option |
| **YouTube** | `search_limit`, `youtube_cookies_file`, `youtube_cookies_browser`, `youtube_ca_bundle` | Auth support |
| **Rate Limiting** | `user_request_limit`, `rate_limit_window`, `voteskip_dynamic`, `voteskip_dynamic_pct` | Per-nick rolling window |
| **Auto-reply** | `auto_reply_enabled`, `auto_reply_interval`, `auto_reply_file` | Scheduled room messages |
| **IM** | `im_auto_reply_enabled`, `im_auto_reply_message`, `im_auto_reply_cooldown`, `im_require_room_presence`, `im_viewer_enabled` | Private message handling |
| **Admin Features** | `admin_mute_mic`, `admin_unmute_mic`, `admin_block_user`, `admin_unblock_user`, `admin_block_bot`, `admin_unblock_bot`, `admin_kick_user`, `admin_ban_user`, `admin_unban_user`, `admin_punish_user`, `admin_punish_bot`, `admin_delete_message_enabled`, `admin_greeting_enabled`, `admin_greeting_message`, `admin_greeting_cooldown` | All config-gated |
| **Welcome** | `welcome_message_enabled`, `welcome_message_message` | First-join greeting |
| **RE Integrations** | `gift_announce_enabled`, `avatar_change_enabled`, `status_indicator_enabled`, `status_alert_enabled` | Camfrog reverse-engineered features |
| **Audio Engineering** | `audio_fade`, `audio_fade_in_sec`, `audio_fade_out_sec`, `audio_normalize` | mpv dynaudnorm |
| **Style** | `message_style` (nested) | GUI preview only |

---

## Audio Engine (`engine.py`, `player.py`)

### `Engine` Class (Main Orchestrator)

#### Initialization
```python
def __init__(self, cfg: Config, adapter: ChatAdapter):
    self.cfg = cfg
    self.adapter = adapter
    self.player = MpvPlayer(cfg)
    self.queue = PlayQueue(shuffle=cfg.shuffle)
    self.index = LocalIndex(scan_folder(...))
    self.router = Router(self)
    self.exec = ThreadPoolExecutor(max_workers=4)
    self.stop_evt = threading.Event()
    self.wake = threading.Event()
    # Circuit breaker state
    self._consecutive_failures = 0
    self._circuit_open = False
    self._circuit_open_time = 0.0
```

#### Main Loops

**Chat Loop** (`_chat_loop`):
- Polls adapter at `cfg.poll_interval` (default 0.5s)
- Parses messages via `router.handle()`
- Handles IM messages separately
- Rate limiting: per-nick rolling window

**Playback Loop** (`_playback_loop`):
- Peeks queue → resolves if needed → plays via `MpvPlayer`
- Circuit breaker: opens after 5 consecutive failures, 60s pause
- Hang detection: polls IPC every 0.5s
- Auto-play mode: activates after `autoplay_idle_timeout` (30s) with no requests
- Announces now/next via `say()`

**Auto-reply Loop** (`_auto_reply_loop`):
- Loads messages from `ads-list.json` (list or dict format)
- Rotates with minimum 60s interval
- Sends to room via `say()`

**IM Auto-reply** (`_im_auto_reply_loop`):
- Cooldown per user (default 60s)
- Only replies if `im_require_room_presence` satisfied

#### Circuit Breaker
```python
# In _playback_loop:
if self._consecutive_failures >= 5:
    self._circuit_open = True
    self._circuit_open_time = time.time()
    self.say("Playback circuit open: too many failures")
    time.sleep(60)  # pause
    self._circuit_open = False
    self._consecutive_failures = 0
```

#### Health Check
```python
def health_check(self) -> dict:
    return {
        "status": "healthy" if not self._circuit_open else "degraded",
        "circuit_open": self._circuit_open,
        "consecutive_failures": self._consecutive_failures,
        "queue_length": len(self.queue.requests) + len(self.queue.pool),
        "current_track": self.current.title if self.current else None,
        "uptime": time.time() - self._start_time,
    }
```

### `MpvPlayer` Class (`player.py`)

#### Key Features
- **One process per track** — `self.proc: subprocess.Popen | None`
- **JSON IPC** — named pipe (Windows) / Unix socket (Linux)
- **Fade in/out** — `afade` filter, configurable duration
- **Hang detection** — polls position every 0.5s; terminate → kill after grace period
- **Graceful timeout** — `mpv_timeout` = duration + grace, never hard cap

#### IPC Commands
```python
# Pause/Resume
{"command": ["set_property", "pause", true]}
{"command": ["get_property", "pause"]}

# Seek
{"command": ["set_property", "time_pos", 30.0]}

# Volume
{"command": ["set_property", "volume", 70]}

# Position/Duration
{"command": ["get_property", "time_pos"]}
{"command": ["get_property", "duration"]}
```

#### Failure Detection
```python
_WHY = ("error", "fail", "not found", "unable", "[ytdl_hook]", "cannot", "no such")

def failure_reasons(log_text: str, keep: int = 4) -> list[str]:
    lines = [ln.strip() for ln in log_text.splitlines() 
             if any(w in ln.lower() for w in _WHY)]
    return lines[-keep:]
```

---

## Playback Queue & Playlist (`playqueue.py`, `playlist.py`)

### `PlayQueue` — Thread-Safe Priority Queue

```python
class PlayQueue:
    def __init__(self, shuffle: bool = True):
        self.requests: list[Track] = []    # User requests (FIFO)
        self.pool: list[Track] = []        # Autoplay pool (shuffled)
        self.shuffle = shuffle
        self.repeat = "off"                # off | one
        self._i = 0                        # Pool index
        self._next_auto: Track | None = None
        self._last: str | None = None      # Last played source (dedup)
        self.lock = threading.RLock()

    def add_request(self, track: Track, position: int | None = None) -> int
    def add_pool(self, tracks: list[Track])
    def pop(self) -> Track | None
    def peek(self) -> Track | None
    def remove(self, index: int) -> Track | None
    def count_by(self, nick: str) -> int
    def shuffle_pool(self)
    def clear_requests(self)
```

**Ordering:** Requests always play first (FIFO), then autoplay pool loops.

### `PlaylistStore` (`playlist.py`) — Persistent JSON

```json
{
  "version": 1,
  "tracks": [
    {"source": "https://youtube.com/watch?v=...", "title": "...", "duration": 245.0,
     "added_by": "Seaza", "added": "2026-10-28T15:10:00"}
  ]
}
```

**Features:**
- Atomic writes (temp + `os.replace()`)
- Deduplication by `source`
- Auto-loads at startup → adds to autoplay pool
- `playlist_dir` — auto-loads all `*.json` from directory
- Max 2000 tracks GUI, 500 autoplay

---

## Command Router (`commands.py`)

### Architecture
```python
COMMANDS: dict[str, tuple] = {}  # name -> (handler, admin_required)

@command(*names, admin=False)
def deco(fn): ...

class Router:
    def __init__(self, engine):
        self.e = engine
        self.last: dict[str, float] = {}           # Global cooldown
        self.user_requests: dict[str, list[float]] = {}  # Per-user rate limit
        self._lock = threading.Lock()              # TOCTOU protection
```

### Commands (30+)

| Command | Aliases | Admin | Description |
|---------|---------|-------|-------------|
| `play` | `p` | No | Queue YouTube URL or search |
| `np` | `now` | No | Now playing |
| `next` | `n` | No | Next in queue |
| `queue` | `q` | No | Show queue |
| `history` | `h` | No | Show history |
| `voteskip` | `vs` | No | Vote to skip current |
| `remove` | `rm` | No | Remove own request by position |
| `skip` | | Yes | Skip current track |
| `pause` | | Yes | Pause playback |
| `resume` | | Yes | Resume playback |
| `vol` | `volume` | Yes | Set volume 0-100 |
| `shuffle` | | Yes | Toggle shuffle |
| `repeat` | | Yes | Toggle repeat off/one |
| `clear` | | Yes | Clear queue |
| `load` | | Yes | Load playlist/source |
| `say` | | Yes | Send message to room |
| `speak` | | Yes | TTS speak |
| `block` | | Yes | Block user |
| `unblock` | | Yes | Unblock user |
| `blockbot` | | Yes | Block bot |
| `unblockbot` | | Yes | Unblock bot |
| `kick` | | Yes | Kick user |
| `ban` | | Yes | Ban user |
| `unban` | | Yes | Unban user |
| `punish` | | Yes | Punish user |
| `punishbot` | | Yes | Punish bot |
| `delete` | | Yes | Delete message by ID |
| `welcome` | | Yes | Toggle/set welcome message |
| `owner` | `เจ้าของห้อง` | Yes | Set room owner |
| `op` | `operator` | Yes | Set room operator |
| `deop` | `เลิกออพ` | Yes | Remove operator |

### Rate Limiting
```python
# Per-user request limit (rolling window)
if len(self.user_requests[nick]) >= self.e.cfg.user_request_limit:
    raise RequestRateLimitError(...)

# Global command cooldown
if time.time() - self.last.get(nick, 0) < self.e.cfg.cooldown:
    return  # silently ignored
```

### Admin Authorization
```python
def is_admin(self, msg) -> bool:
    # Nickname-based (SPOOFABLE - documented)
    return msg.user.lower() in [a.lower() for a in self.e.cfg.admins]
```

---

## Chat Adapters (`adapters/`)

### Abstract Base (`base.py`)
```python
class ChatAdapter(ABC):
    @abstractmethod
    def messages(self) -> Iterator[ChatMessage]: ...
    @abstractmethod
    def send(self, text: str) -> None: ...
    def close(self) -> None: ...

def parse_line(line: str, rx: re.Pattern, is_im: bool = False) -> ChatMessage | None
def diff_lines(prev: list[str], cur: list[str]) -> list[str]
```

### `UiaAdapter` (`uia.py`) — Primary Production Adapter

**Two Layouts:**
1. **Web** (Camfrog room): embedded web panes — see `webchat.py`
2. **Text**: Document/Edit controls — `view_type`/`view_index`, `input_type`/`input_index`

**Send Modes:**
- **Background** — `PostMessageW` to HWND, no focus steal
- **Foreground** — Focus window, `SetForegroundWindow`, paste via clipboard
- **Auto** — Try background, verify line appeared, fallback to foreground

**Key Methods:**
```python
def _ensure_controls(self) -> bool:
    # Finds window, history pane, input control
    # Caches handles; refreshes on failure

def _send_bg(self, text: str) -> bool:
    # Background send via winmsg.py
    # Strategies: UIA ValuePattern → UIA TextPattern → Win32 WM_SETTEXT

def _send_fg(self, text: str) -> bool:
    # Foreground send: focus window, click input, paste, Enter

def send(self, text: str) -> None:
    # Routes based on cfg.send_mode
    # Auto mode verifies via diff_lines()
```

### `ConsoleAdapter` (`console.py`) — Testing
- `stdin`/`stdout` chat
- `!play x` = admin; `nick: !play x` = that user
- `im nick: text` = private message

### `LogTailAdapter` (`logtail.py`) — Read-Only
- Tails chat log file
- Pairs with `chat_sender="uia"`
- Detects IM via `[IM]` prefix

---

## GUI Architecture (`gui.py`)

### `App` Class (3,252 lines) — Tkinter Main Window

#### Visual Design
- **Dark studio theme**: `#0a0b12` background, aurora gradients
- **Animated vinyl record** — rotates while playing
- **Equalizer bars** — decorative, 30 FPS animation
- **Progress/Volume bars** — glowing, clickable seek
- **Particles/Confetti** — on track completion

#### Tabs
| Tab | Content |
|-----|---------|
| **Queue** | Current track + queue list (requests + pool) |
| **History** | Completed tracks with timestamps |
| **Chat** | Live room chat log |
| **IM** | Private messages (if `im_viewer_enabled`) |
| **Settings** | Modal popup with all config options |

#### Concurrency Model
```python
# All GUI mutations from workers:
self.after(0, lambda: self._update_ui(...))

# Reentrancy guards:
self._loading_folder = True  # during folder scan
self._set_adding_state(True) # during track add

# Timer cleanup:
self.after_cancel(self._anim_id)
self.after_cancel(self._poll_id)
```

#### Settings Dialog (`open_settings`)
- **Toplevel** popup (not modal, but single-instance)
- **24 checkboxes** as `PillButton` with typed annotations
- **FontEditor** preview panel (rich text for GUI only)
- **Live validation** on save → `Config.save()`

#### Key Widgets
- `PillButton` — Custom canvas button (icon, hover, press, active states)
- `VolSlider` — Canvas volume slider (click + drag)
- `RoundRect` — Rounded rectangle drawing

---

## Camfrog Integration

### Window Discovery (`discover.py`, `windows.py`)

**Auto-discovery** (`--discover` or `auto_discover=true`):
1. Enumerate top-level windows via `pywinauto`
2. Filter by process exe name (`(?i)camfrog`)
3. Score candidates by chat line count
4. Find Document/Edit controls for history/input
5. Write `view_type`, `view_index`, `input_type`, `input_index` to config

**Web View Detection:**
- History pane: `wb-log-room-data` substring
- Input pane: `wb-edit-data` substring
- Parsed via `webchat.py` (avatar = message boundary)

### RE Integrations (Reverse-Engineered)

| Feature | Detection | Config |
|---------|-----------|--------|
| **Gift Announcements** | Keywords in chat: "gift", "sent a gift" | `gift_announce_enabled` |
| **Avatar Changes** | "changed avatar", "updated profile picture" | `avatar_change_enabled` |
| **Status Indicators** | Online/Away/Busy/Invisible/Admin/Moderator/Owner | `status_indicator_enabled` |
| **Upgrade/Payment Alerts** | "upgrade required", "payment required" | `status_alert_enabled` |
| **Name Color Tracking** | Hex color in style attribute | GUI preview only |

**Implementation:** `engine._handle_re_events()` scans chat lines for patterns.

### Background Messaging (`winmsg.py`)

```python
# Win32 PostMessageW to HWND — no focus steal
# Strategies for Chromium web editor:
# 1. UIA ValuePattern.SetValue()
# 2. UIA TextPattern.Replace()
# 3. WM_SETTEXT + WM_CHAR (VK_RETURN)
# 4. Foreground fallback (focus + paste)
```

### Font Registry (`camfrog_font.py`)

**Registry Paths:**
```
HKEY_CURRENT_USER\Software\Camfrog\Camfrog
HKEY_CURRENT_USER\Software\Camfrog Video Chat\Camfrog
HKEY_CURRENT_USER\Software\Camfrog\Settings\General
```

**Keys:** `IMFont`, `IMFontSize`, `FontName`, `FontName_VCHR`

**Note:** Receiver-side display only — does NOT affect outgoing messages.

---

## Library & YouTube (`library.py`)

### `LocalIndex` — Local File Catalog

```python
class LocalIndex:
    def __init__(self, tracks: list[Track])
    def find(self, query: str) -> list[Track]   # Fuzzy match by title
    def get(self, source: str) -> Track | None
```

### `scan_folder(path, max_dirs=50, limit=500, recursive=True)`

**Safety Rules:**
- **Never follows symlinks** — `entry.is_symlink()` → `continue`
- **Bounded recursion** — `max_dirs` cap (50 autoplay, 0 = unlimited manual)
- **Bounded results** — `limit` cap (2000 GUI, 500 autoplay)
- **Permission resilience** — `PermissionError` caught per-entry
- **Metadata fallback** — `mutagen` errors → filename

**Supported Extensions:**
```python
AUDIO = {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".opus", ".aac"}
VIDEO = {".mp4", ".mkv", ".webm", ".avi", ".mov"}
MEDIA = AUDIO | VIDEO
```

### YouTube Resolution

```python
def remote_tracks(query: str, cfg: Config) -> list[Track]:
    # 1. If URL → direct yt-dlp
    # 2. If ytsearchN: → yt-dlp search
    # 3. Plain text → ytsearch{cfg.search_limit}: (default 1)
    # 4. Returns Track[] with title, duration, source URL
```

**Authentication:**
- `youtube_cookies_file` — Netscape cookies.txt
- `youtube_cookies_browser` — `--cookies-from-browser` (chrome/edge/firefox)
- `youtube_ca_bundle` — Custom CA PEM for cert verification

---

## Text & Rendering (`textutil.py`, `renderer.py`, `messages.py`)

### `clean_text()` / `norm()` (`textutil.py`)
```python
def clean_text(s: str) -> str:
    """One line, no control chars, single spaces."""
    return " ".join(_CTRL.sub(" ", s).split())

def norm(s: str) -> str:
    """Comparison form: NBSP/whitespace collapsed, case kept."""
    return " ".join(s.replace("\xa0", " ").split())
```

### `MessageRenderer` (`renderer.py`)

**Critical:** Camfrog does NOT support rich text in outgoing messages.

```python
class MessageRenderer:
    def render(self, text: str, style: MessageStyle) -> RenderedMessage:
        # For SENDING: always plain_text
        # For GUI PREVIEW: rich_text + preview_tags for tkinter Text
```

### `messages.py` — 300+ String Keys (EN/TH)

**Categories:**
- Core: `help_base`, `help_admin`, `error`, `admin_only`
- Queue: `queued_one`, `queue_full`, `max_requests`
- Playback: `now_playing`, `next_up`, `paused`, `resumed`
- Admin: `skip_ok`, `vol_set`, `blocked`, `unblocked`, `kicked`, `banned`
- RE: `gift_announce`, `avatar_changed`, `status_changed`, `upgrade_alert`
- IM: `im_only_command`, `im_user_not_in_room`, `im_auto_reply`
- GUI: `g_*` prefixes (300+ labels)

---

## Security Model

### Threat Model & Mitigations

| Threat | Mitigation |
|--------|------------|
| **Nickname spoofing** | Documented in-code; fail-closed when `admins = []` |
| **IM command injection** | `im_require_room_presence = true` (default) |
| **Blocked user info leak** | Silently ignored — no error messages |
| **Shell injection** | Zero `shell=True`; all `subprocess` use arg lists |
| **Unsafe deserialization** | Only `tomllib` + `json` (stdlib); no `pickle`/`yaml` |
| **Config tampering** | Fail-closed validation with exact line markers |
| **Path traversal** | `resolve_executable()` validates paths |
| **Secrets in repo** | `.env.example` only; real `.env` gitignored |

### Admin Authorization
```python
# In commands.py:Router.is_admin()
def is_admin(self, msg) -> bool:
    # NOTE: Nickname-based auth is SPOOFABLE
    # Any user can adopt an admin's nickname
    return msg.user.lower() in [a.lower() for a in self.e.cfg.admins]

# Local console messages (msg.local=True) always trusted as admin
```

### IM Security
```python
# In engine.py: IM command handling
if msg.is_im:
    if not self.cfg.im_require_room_presence:
        # Allow — but logged
    elif nick not in self._seen_in_room:
        raise UserError(self.t("im_user_not_in_room"))
```

---

## Concurrency & Threading

### Thread Architecture

| Thread | Purpose | Communication |
|--------|---------|---------------|
| **Main (GUI)** | Tkinter event loop | `tk.after(0, callback)` |
| **Engine** | Chat loop, playback loop, auto-reply | `threading.Event`, `queue.Queue` |
| **Executor** | `ThreadPoolExecutor(4)` — blocking I/O | `Future` callbacks |
| **TTS** | Dedicated COM STA thread | `queue.Queue` + worker |
| **Player IPC** | mpv JSON IPC polling (0.5s) | `threading.Event` |

### Synchronization Primitives

```python
# Engine
self.stop_evt = threading.Event()      # Global shutdown
self.wake = threading.Event()          # Wake playback loop
self.exec = ThreadPoolExecutor(4)      # Worker pool
self._lock = threading.Lock()          # Router TOCTOU protection

# PlayQueue
self.lock = threading.RLock()          # All queue operations

# TTS
_tts_queue: queue.Queue[Callable[[], None] | None] = queue.Queue()
_tts_lock = threading.Lock()
```

### Cancellation & Cleanup

```python
def shutdown(self):
    self.stop_evt.set()
    self.wake.set()
    self.player.stop()
    self.adapter.close()
    self.exec.shutdown(wait=False, cancel_futures=True)
    # Join daemon threads...
```

---

## Build & Deployment

### PyInstaller Build (`build.ps1`, `Makefile`)

```bash
# Windows
powershell.exe -NoProfile -ExecutionPolicy Bypass -File build.ps1

# Output: dist/AutoDJ.exe (single-file or onedir)
```

**Spec:** `AutoDJ.spec` — includes mpv, yt-dlp, ffmpeg, python deps

### NSIS Installer (`installer.nsi`)

**Sections:**
- `SEC_MAIN` — AutoDJ.exe, config.toml, ads-list.json, README, CHANGELOG, LICENSE
- `SEC_PLAYLIST` — `playlist\*.json` (34 files, 274 tracks)
- `SEC_MPV` — mpv.exe, yt-dlp.exe, `_internal\*`, mpv-register.bat
- `SEC_VBCABLE` — Optional virtual audio driver
- `SEC_DOCS` — `docs\*`
- `SEC_TOOLS` — `tools\*`
- `SEC_SCRIPTS` — `scripts\*`

**Features:**
- Install to `%APPDATA%\CamfrogAutoDJ` (user-writable)
- Preserves `config.toml`, `playlist.json` on upgrade
- Uninstaller preserves user data
- Creates Start Menu shortcut
- Registers mpv file associations (optional, admin)

### Validation Pipeline (`Makefile`)

```make
full-validation: lint typecheck validate-playlists test changelog-check config-check validate-installer

lint: ruff check camfrog_autodj tests tools
typecheck: mypy --check-untyped-defs camfrog_autodj tests tools
validate-playlists: python tools/validate_playlists.py
test: pytest -q -p no:faulthandler -p no:cacheprovider
config-check: python -c "from camfrog_autodj.config import Config; Config.load('config.toml')"
validate-installer: python tools/validate_installer.py
```

### Validation Results (Current)

| Gate | Status |
|------|--------|
| Mypy (strict) | ✅ 0 errors / 62 files |
| Ruff Lint | ✅ All pass |
| Ruff Format | ✅ 62 files formatted |
| Pytest | ✅ 375 passed, 3 subtests |
| Playlist Validation | ✅ 34 files, 274 tracks, 0 invalid |
| Config Check | ✅ Valid TOML, 56 keys |
| Installer Validation | ✅ NSIS structure verified |
| **Full Pipeline** | ✅ **Exit 0** |

---

## Missing / Future Enhancements

### Identified Gaps (from `docs/engineering/IMPLEMENTATION-PLAN.md`)

| Item | Status | Priority |
|------|--------|----------|
| **Extract `ChatProcessor`, `PlaybackManager`, `ConfigManager` from Engine** | TODO | High — Engine does too much (1,569 lines) |
| **GUI-Engine interface/adapter boundary** | TODO | High — Tight coupling |
| **Dependency injection** | TODO | Medium |
| **Integration tests (end-to-end)** | TODO | High |
| **Penetration/security test suite** | TODO | High |
| **Config schema documentation** | TODO | Medium |
| **`__all__` exports in all modules** | TODO | Low |
| **Name color tracking in GUI preview** | TODO | Low |

### Performance Opportunities

| Area | Current | Potential Improvement |
|------|---------|----------------------|
| **Playlist loading** | Sync at startup | Async/background load |
| **LocalIndex search** | Linear scan | Trie/prefix tree for fuzzy match |
| **IPC polling** | 0.5s fixed | Adaptive (faster when playing) |
| **GUI animation** | 30 FPS always | Pause when minimized/hidden |

### Security Hardening

| Feature | Status |
|---------|--------|
| **Signed config verification** | Not implemented |
| **Replay attack protection** | Not implemented (nonce/timestamp) |
| **Audit logging** | Basic logging only |
| **Rate limit persistence** | In-memory only |

### Platform Support

| Platform | Status |
|----------|--------|
| **Windows (primary)** | ✅ Full support |
| **Linux (headless)** | ✅ Console mode works |
| **macOS** | ❌ Not tested |
| **ARM64** | ❌ Not tested |

---

## Appendix: File Structure

```
camfrog-autodj/
├── camfrog_autodj/
│   ├── adapters/
│   │   ├── __init__.py     # Composite, NullAdapter, build_adapter
│   │   ├── base.py         # ChatAdapter, ChatMessage, parse_line
│   │   ├── console.py      # ConsoleAdapter
│   │   ├── logtail.py      # LogTailAdapter
│   │   └── uia.py          # UiaAdapter (primary)
│   ├── __init__.py         # Version, exports
│   ├── __main__.py         # CLI entry point
│   ├── camfrog_font.py     # Windows registry font settings
│   ├── clipkeys.py         # Clipboard keybindings
│   ├── commands.py         # Command router (30+ commands)
│   ├── config.py           # Config with validation
│   ├── discover.py         # Window auto-discovery
│   ├── doctor.py           # Diagnostics
│   ├── engine.py           # Main orchestration
│   ├── exceptions.py       # Exception hierarchy
│   ├── gui.py              # Tkinter GUI (3,252 lines)
│   ├── launcher.py         # Camfrog launch
│   ├── library.py          # Local index, yt-dlp
│   ├── messages.py         # EN/TH strings
│   ├── migrate.py          # Config migration
│   ├── models.py           # Track, fmt_time
│   ├── paths.py            # Executable resolution
│   ├── player.py           # MpvPlayer (IPC, fade, hang)
│   ├── playlist.py         # PlaylistStore (JSON)
│   ├── playqueue.py        # PlayQueue (thread-safe)
│   ├── renderer.py         # Message rendering
│   ├── textutil.py         # clean_text, norm
│   ├── tts.py              # pyttsx3 TTS
│   ├── visuals.py          # Animation helpers
│   ├── webchat.py          # Web view parsing
│   ├── windows.py          # Window enumeration
│   └── winmsg.py           # Win32 background send
├── playlist/               # 34 JSON files, 274 tracks
├── tools/
│   ├── validate_playlists.py
│   └── validate_installer.py
├── tests/                  # 23 test modules, 375 tests
├── docs/                   # Architecture, audit, RE evidence
├── scripts/                # Build, bootstrap, validation
├── installer.nsi           # NSIS installer
├── build.ps1               # PyInstaller build
├── Makefile                # Validation pipeline
├── pyproject.toml          # Project config (mypy, ruff, pytest)
├── config.toml             # Production config (bundled with installer)
├── config.example.toml     # Example config (manual setups)
├── README.md
├── CHANGELOG.md
├── AGENTS.md
├── SECURITY.md
├── ROADMAP.md
└── FINAL-AUDIT-REPORT.md
```

---

## Appendix: Key Configuration Defaults (v0.3.0)

```toml
# Identity
bot_nick = "AutoDJ"
prefix = "!"
lang = "en"

# Chat
chat_reader = "uia"
chat_sender = "uia"
send_mode = "auto"
send_verify = true

# Audio
mpv_path = "mpv/mpv.exe"
ytdlp_path = "mpv/yt-dlp.exe"
audio_device = "auto"
volume = 70
mpv_timeout = 30.0

# Library
playlist_dir = "playlist"
shuffle = true
max_queue = 50
max_duration = 900

# Limits
max_requests_per_user = 3
voteskip_threshold = 3
cooldown = 3.0
user_request_limit = 5
rate_limit_window = 300.0

# Auto-reply
auto_reply_enabled = true
auto_reply_interval = 300.0
auto_reply_file = "ads-list.json"

# IM
im_auto_reply_enabled = true
im_auto_reply_cooldown = 60.0
im_require_room_presence = true
im_viewer_enabled = true

# Admin (all enabled by default)
admin_mute_mic = true
admin_unmute_mic = true
admin_block_bot = true
admin_unblock_bot = true
admin_kick_user = true
admin_ban_user = true
admin_unban_user = true
admin_punish_user = true
admin_punish_bot = true
admin_delete_message_enabled = true
admin_greeting_enabled = true

# Welcome
welcome_message_enabled = true

# RE Integrations
gift_announce_enabled = true
avatar_change_enabled = true
status_indicator_enabled = true
status_alert_enabled = true

# Audio Engineering
audio_fade = true
audio_fade_in_sec = 1.2
audio_fade_out_sec = 1.5
```

---

*Blueprint generated from source code analysis — CamfrogAutoDJ v0.3.0*