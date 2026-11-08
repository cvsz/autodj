# Architecture Review — cvsz/autodj

## Layered architecture (verified against source)

AutoDJ follows a clean, layered, thread-safe architecture:

```
CLI (__main__.py)  ->  Engine (engine.py)  ->  adapters (chat I/O)
                      ->  Player (player.py) -> mpv subprocess
                      ->  Library (library.py) -> local files + yt-dlp
                      ->  PlayQueue (playqueue.py) -> requests + autoplay pool
                      ->  Playlist (playlist.py) -> persistent playlist.json
                      ->  Config (config.py) -> validated TOML
GUI (gui.py) polls Engine.snapshot() ~2x/sec; animates ~30fps
```

### Modules and responsibilities

| Module | Responsibility | Thread safety |
|--------|---------------|---------------|
| `__main__.py` | CLI, config load, APPDATA relocation, auto-launch/discover, adapter build, GUI/console/headless modes | startup only |
| `config.py` | TOML loading + validation (46 settings, types/ranges/regexes/choices, "did you mean") | immutable after load |
| `engine.py` | Core playback loop, queue mgmt, track resolution, YouTube playlist detection, backoff, structured diagnostics, TTS, auto-reply, IM auto-reply | RLock + Events |
| `commands.py` | Command router: cooldown, sliding-window rate limit, admin/blocked handling, all `!` commands EN+TH | uses engine lock |
| `player.py` | mpv subprocess per track, IPC (`get_time_pos`, `seek`, `set_pause`, `set_volume`), fade in/out, hang detection (grace period, not cap) | Lock per player |
| `playqueue.py` | Request-first queue + autoplay pool, shuffle, repeat, identity-based removal | RLock |
| `playlist.py` | Persistent `playlist.json`, atomic writes (tmp+replace), `.corrupt-<ts>` backup, URL validation | Lock |
| `library.py` | Local folder scanning (symlink-safe, limit/max_dirs caps), yt-dlp resolution (exe then module) | pure functions |
| `models.py` | `Track` dataclass, `UserError`, `YtdlpMissingError`, `fmt_time` | immutable data |
| `gui.py` | Tkinter studio window, animations, Queue/History/Chat tabs, Settings tab with atomic save | main thread only; `after()` for cross-thread UI |
| `adapters/*` | `uia` (Windows UI Automation), `console` (stdin), `logtail` (read-only file tail) | uia: COM lock |
| `discover.py` | Auto-discover room window + chat controls, atomic config save | Windows only |
| `launcher.py` | Auto-launch Camfrog + join URI, Windows only | Windows only |
| `doctor.py` | `--check` diagnostics | read-only |
| `tts.py` | Serialized pyttsx3 worker thread (COM STA thread-safety) | dedicated worker thread |
| `webchat.py` | Embedded web-view chat parsing (avatar-split boundaries) | pure |
| `windows.py`/`winmsg.py`/`clipkeys.py` | Window enumeration/resolution, Win32 posted messages, Tk clipboard on any layout | Windows only |

### Design qualities confirmed

- **No blocking I/O on GUI thread:** folder scans, YouTube lookups, and playback run on `ThreadPoolExecutor` (8 workers) or daemon threads; GUI polls via `after()`.
- **No orphaned processes:** `MpvPlayer.stop()` terminates/kills mpv; `Engine.shutdown()` joins threads with 5s timeout.
- **Symlink safety:** `scan_folder` never follows symlinks (avoids cycles and slow Windows reparse points); `limit`/`max_dirs` caps prevent runaway scans.
- **Atomic persistent writes:** `playlist.save_playlist` (tmp+replace), `discover.save_config` (bak+tmp+replace), GUI `save_settings` (bak+tmp+replace).
- **Fail-closed config:** unknown keys, bad types, out-of-range, invalid regexes all raise explicit `ConfigError`.
- **Certificate verification always preserved:** yt-dlp TLS never disabled; custom CA bundle via `certifi.where()` patch (module path only).
- **COM serialization:** `UiaAdapter.com_lock` (RLock) serializes UIA reader/sender; pyttsx3 single worker thread.

### Assessment

Architecture is sound. No circular dependencies, no unnecessary rewrites indicated. Existing architecture maintained.
