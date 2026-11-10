# AutoDJ Architecture

## Purpose

CamfrogAutoDJ is a music bot for Camfrog rooms. It plays YouTube tracks and local audio files (mp3, mp4, flac, ogg, opus, aac, wav, mkv, webm, avi, mov) into a Camfrog room chat, responds to `!` commands (and Thai aliases), manages a request queue, and provides a desktop GUI. It runs on Windows (primary) and can be tested on Linux/macOS/WSL.

## High-level structure

```
AutoDJ.exe (frozen PyInstaller binary)
├── camfrog_autodj/__main__.py   — CLI entry point: --check, --discover, --windows, --dump, --say, --gui, --console
├── camfrog_autodj/engine.py     — Engine: chat loop, player loop, command router, autoplay pool
├── camfrog_autodj/commands.py   — Router: command registration, admin authorization, cooldowns, rate limits
├── camfrog_autodj/config.py     — Config: TOML loading, validation, defaults
├── camfrog_autodj/player.py     — MpvPlayer: one mpv process per track, IPC control, fade in/out
├── camfrog_autodj/library.py    — Library: yt-dlp lookups (exe or module), local file scanning, URL parsing
├── camfrog_autodj/playlist.py   — PlaylistStore: persistent playlist.json (atomic write, dedup by source)
├── camfrog_autodj/playqueue.py  — PlayQueue: requests-first queue + autoplay pool, shuffle/repeat
├── camfrog_autodj/discover.py   — Auto-discover: finds Camfrog room window and chat controls
├── camfrog_autodj/adapters/     — Chat adapters: uia (UI Automation), webchat (embedded web panes), console
├── camfrog_autodj/gui.py        — GUI: Tk-based studio window with queue/history/chat/TTS
├── camfrog_autodj/doctor.py     --check: plain-language setup diagnostics
├── camfrog_autodj/messages.py   — All user-facing strings (English + Thai)
├── camfrog_autodj/textutil.py   — Text sanitisation (control characters stripped)
├── camfrog_autodj/tts.py        — Text-to-speech via pyttsx3 (SAPI)
├── camfrog_autodj/paths.py      — Executable path resolution (explicit > beside mpv > PATH)
├── camfrog_autodj/windows.py    — Window enumeration and resolution for Camfrog discovery
└── camfrog_autodj/winmsg.py     — Windows message posting for background chat sending
```

## Runtime layers

### 1. Configuration (`config.py`, `config.toml`)

`config.toml` is loaded with `tomllib` and validated against the `Config` dataclass:
- Unknown keys are rejected with "did you mean" suggestions
- Types are enforced (bool/int/float/str/list) with bool excluded from int checks
- Choice fields (lang, chat_reader, view_kind, send_mode) are constrained
- Ranges are validated (volume 0–100, max_duration 1–604800, etc.)
- Regular expressions are compiled before acceptance
- Relative log paths are resolved to `%APPDATA%\CamfrogAutoDJ\` so they are writable even when installed to Program Files
- Non-writable `config.toml` is relocated to APPDATA at startup

### 2. Chat I/O (`adapters/`, `webchat.py`, `winmsg.py`)

Two transport paths:
- **uia** (Windows UI Automation via pywinauto): attaches to the Camfrog room window, reads chat history lines, posts messages via background (WM_SETTEXT / posted messages) or foreground (clipboard + paste) send modes
- **console** (testing): stdin/stdout, always trusted as admin
- **webchat**: handles Camfrog's embedded web-view chat panes (`wb-log-room-data`, `wb-edit-data`)

Background sending verifies the message appeared in the room; after 2 unconfirmed sends it falls back to foreground mode. All UIA access is serialized with a COM re-entrancy lock.

### 3. Command dispatch (`commands.py`)

Commands are registered with `@command(names, admin=False)`. The `Router`:
- Requires messages to start with the configured prefix (`!` by default)
- Authorizes admins by display nick (case-insensitive) — see security notes below
- Enforces per-user cooldowns and sliding-window request limits (non-admin only)
- Blocks listed users silently (no room reply)
- Admin commands: pause, resume, vol, shuffle, repeat, clear, load, say, speak, block, unblock
- User commands: play, np, next, queue, history, voteskip, remove, help

### 4. Playback (`player.py`, `library.py`)

One `mpv` process per track:
- `--no-video --force-window=no --no-terminal --really-quiet` (no GUI flash)
- IPC server for pause/volume control
- Log file captured for failure diagnosis
- Fade-in/fade-out via volume ramping thread
- `mpv_timeout` is a grace period on top of known track length, never a hard cap
- yt-dlp path is resolved once and passed to mpv via `--script-opts=ytdl_hook-ytdl_path`
- On failure: exponential backoff (1s → 30s cap), max 3 failure announcements in the room, then log-only

### 5. Library and lookups (`library.py`)

yt-dlp resolution order:
1. Explicit `ytdlp_path` from config (fail-closed if it doesn't exist)
2. `yt-dlp.exe` next to `mpv.exe`
3. `yt-dlp` on PATH
4. `yt_dlp` Python module (for title lookups when no executable is available)

Supports YouTube URLs, playlist URLs, `ytsearchN:` queries, and local file/folder scanning.

### 6. Auto-discovery (`discover.py`, `windows.py`)

At startup (`auto_discover = true`) or via `--discover`, scans visible Camfrog windows and identifies:
- Chat history control (Document/Edit or web pane)
- Message box input control
- Writes `window_title_re`, `view_type/view_index`, `input_type/input_index` to `config.toml` atomically (tmp + replace, with `.bak` backup)
- Never replaces a working config with invalid TOML

## Trust boundaries and security

### Authentication / authorization

Camfrog UI automation exposes only display nicks — there is no cryptographic identity. Admin authorization (`commands.py:32`) is nickname-based and case-insensitive:
```python
return msg.local or msg.user.lower() in self.e.admins
```

**Limitation:** anyone who can display the same nick (look-alike characters, a nick freed by disconnect) gains admin rights. Mitigations:
- `admins = []` by default in `config.example.toml` — operator must add their nick
- `doctor.py --check` warns when `admins` is empty
- Blocked users cannot block themselves or other admins
- Blocked users' commands are ignored silently (no room noise)

### Input validation

- All outgoing text is sanitised by `clean_text()` (control characters stripped, whitespace collapsed)
- Wrapped message continuations are prefixed with `…` so they never look like commands
- `!load` rejects absolute paths outside configured `music_dirs`
- `!play` restricts non-admin users to `allowed_hosts` (YouTube only by default)
- Live streams and tracks exceeding `max_duration` are refused for non-admin users

### Secrets hygiene

- No credentials, tokens, or keys are committed
- `build.ps1` copies `config.toml` into `dist\` — operators must not distribute `dist\` as-is
- `AUTODJ_PFX_PASSWORD` environment variable preferred over `-Password` (shell history)

## Installer and distribution

- **NSIS installer** (`installer.nsi`): per-user install to `%APPDATA%\CamfrogAutoDJ`, preserves `config.toml` and `playlist.json` on upgrade, uninstaller removes only application-owned files
- **PowerShell installers** (`install.ps1`, `install-full-auto.ps1`): staging-based installation with user-data backup/restore before any directory removal
- **Build** (`build.ps1`): PyInstaller one-file exe, self-signing or real code-signing cert, `--noupx`, smoke-tested with `--version`
- **Release workflow** (`.github/workflows/release.yml`): validation gate (tests, lint, typecheck, secret scan) before builder job; no automatic publish during remediation

## Concurrency

- `ThreadPoolExecutor(8)` for yt-dlp lookups so `!skip` and friends stay responsive
- Chat reader thread polls at `poll_interval` (default 0.5 s)
- Player loop processes the queue sequentially
- Sender thread serializes all chat output with `send_interval` flood control
- All UIA access is protected by a re-entrant COM lock
- TTS uses a dedicated lock so overlapping clips don't un-duck music early

## What is NOT tested

- Real Camfrog client, mpv, yt-dlp, or TTS voices
- `build.ps1` execution
- Windows launch/URI handling
- On-screen GUI appearance (Tk smoke test runs where a display exists)
