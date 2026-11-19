# Architecture — CamfrogAutoDJ v0.3.8

**Date:** 2026-11-16  
**Branch:** main (HEAD: fecc053)  
**Detailed documentation:** `docs/architecture.md`

---

## Executive Summary

CamfrogAutoDJ is a music bot for Camfrog rooms that plays YouTube tracks and local audio files, responds to `!` commands (with Thai aliases), manages a request queue, and provides a desktop GUI. It runs on Windows (primary) and can be tested on Linux/macOS/WSL.

The architecture is documented in detail at `docs/architecture.md`. This file provides a concise overview.

---

## High-Level Structure

```
AutoDJ.exe (frozen PyInstaller binary)
├── camfrog_autodj/__main__.py   — CLI entry point
├── camfrog_autodj/engine.py     — Engine: chat loop, player loop, command router, autoplay pool
├── camfrog_autodj/commands.py   — Router: command registration, admin auth, cooldowns, rate limits
├── camfrog_autodj/config.py     — Config: TOML loading, fail-closed validation, defaults
├── camfrog_autodj/player.py     — MpvPlayer: one mpv per track, IPC control, fade in/out
├── camfrog_autodj/library.py    — Library: yt-dlp lookups, local file scanning, URL parsing
├── camfrog_autodj/playlist.py   — PlaylistStore: persistent playlist.json (atomic write, dedup)
├── camfrog_autodj/playqueue.py  — PlayQueue: requests-first queue + autoplay pool, shuffle/repeat
├── camfrog_autodj/discover.py   — Auto-discover: finds Camfrog window and chat controls
├── camfrog_autodj/adapters/     — Chat adapters: uia, webchat, console, null
├── camfrog_autodj/gui.py        — GUI: Tk studio window with queue/history/chat/TTS
├── camfrog_autodj/doctor.py     --check: plain-language setup diagnostics
├── camfrog_autodj/messages.py   — All user-facing strings (EN + TH)
├── camfrog_autodj/textutil.py   — Text sanitisation
├── camfrog_autodj/tts.py        — Text-to-speech via pyttsx3 (SAPI)
├── camfrog_autodj/paths.py      — Executable path resolution
├── camfrog_autodj/windows.py    — Window enumeration for Camfrog discovery
├── camfrog_autodj/winmsg.py     — Windows message posting for background chat
├── camfrog_autodj/webhook/      — FastAPI webhook server with HMAC verification
└── camfrog_autodj/plugins/      — Plugin system (stats, help builtins)
```

---

## Runtime Layers

### 1. Configuration (`config.py`, `config.toml`)
- TOML loaded with `tomllib`, validated against `Config` dataclass
- Fail-closed: `ConfigError` with exact line + `^` marker
- Validation order: type → choices → ranges → regexes → semantic
- Atomic writes: temp file + `os.replace()` + `.bak` backup
- Auto-relocation to `%APPDATA%\CamfrogAutoDJ\` when not writable

### 2. Audio Engine (`player.py`, `engine.py`)
- **One mpv process per track** — no shared state between tracks
- JSON IPC for control (pause, resume, seek, volume) via named pipe (Windows) / Unix socket (Linux)
- `mpv_timeout` is a grace period (duration + timeout), never a hard cap
- Hang detection at 0.5s poll; terminate → kill after grace period exceeded
- Resource cleanup: IPC log files removed; `proc` reference cleared
- No audio I/O on GUI thread — playback in background thread

### 3. GUI Concurrency (`gui.py`)
- Tkinter mainloop owns the window — no blocking I/O on main thread
- Cross-thread updates via `tk.after(0, ...)`
- Reentrancy guards: buttons disabled during async operations
- Cancellation: `stop_evt` propagated to all workers
- Timer cleanup: `after_cancel` on window close

### 4. Library Scanning (`library.py`)
- Never follows symlinks (`entry.is_symlink()` → `continue`)
- Bounded recursion (`max_dirs` cap) and bounded results (`limit` cap)
- Permission resilience: `PermissionError` caught per-entry
- Metadata fallback: `mutagen` errors caught; fall back to filename

### 5. Chat Adapters (`adapters/`)
- UIA (Windows UI Automation), LogTail (read-only), Console (testing), NullAdapter (fallback)
- COM lock serializes reader/sender access
- Background send with verify + foreground fallback (`send_mode = auto`)
- Automatic fallback chain: `uia` → `logtail` → `console` → `null`

### 6. Webhook API (`webhook/`)
- FastAPI + uvicorn, lazy imports (optional dependency)
- `app.state` dependency injection — no global mutable state
- HMAC-SHA256 signature verification
- Per-IP rate limiting; CORS; health and metrics endpoints

### 7. Plugin System (`plugins/`)
- Type-safe `Plugin` / `PluginInterface` ABC
- `PluginManager` with load/unload and event emission
- Builtin plugins: `stats`, `help`

---

## Key Design Principles

| Principle | Implementation |
|-----------|---------------|
| Fail-closed | `ConfigError` on any invalid value; `admins = []` → no admin access |
| One process per track | `MpvPlayer` spawns one mpv subprocess per track |
| Graceful degradation | Adapter fallback chain; circuit breakers for playback/chat |
| No secrets in code | `.env` gitignored; `.env.example` only; no hardcoded credentials |
| Atomic writes | Temp file + `os.replace()` + `.bak` for config and playlist |
| Windows primary, Linux headless | Named pipes (Windows) / Unix sockets (Linux) for mpv IPC |

---

## See Also

- `docs/architecture.md` — Detailed architecture documentation
- `docs/adr/` — Architecture decision records
- `docs/protocols/` — Reverse-engineering evidence (Camfrog font logic, UIA behavior)
