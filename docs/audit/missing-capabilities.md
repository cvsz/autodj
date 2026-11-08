# Missing Capabilities — Camfrog AutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`  
**Status:** Classified, not concealed

## Not implemented on this host (BLOCKED / NOT IMPLEMENTED)

| Capability | Reason |
|------------|--------|
| GPG-signed commits as cvsz | `GPG_PASSPHRASE` unset, no TTY (F-005) |
| Windows PyInstaller `.exe` build | No Windows host / PyInstaller Windows run |
| NSIS installer build + `makensis` | No Windows host / NSIS |
| Authenticode signature verification | No signing host / no Windows |
| Installer install/uninstall/upgrade test | No Windows host |
| Real Camfrog UI Automation integration | No authorized Camfrog test environment |
| Real mpv audio playback | No mpv / audio device / Windows on this host |
| Real yt-dlp YouTube lookups against live YouTube | No network target authorized; no real media |
| TTS (pyttsx3) live | Windows SAPI only; no Windows host |
| Real-Tk GUI rendering on screen | No display / Camfrog window |
| Docker build | Not part of executed commands; no container target |

## Capabilities implemented and tested

- Library scanning with symlink/reparse-point safety, limits, unreadable-dir handling (11 new tests).
- Playlist atomic save, corrupt-file backup, dedup (existing tests).
- Play queue, shuffle, repeat, rate limiting, cooldown, commands EN/TH (existing tests).
- Config validation and migration (existing tests).
- Chat echo prevention, failure backoff, flood control (existing tests).
- GUI thread-safe marshaling via `after(0, ...)` (reviewed; real-Tk smoke test environment-dependent).

## Policy note

Missing features are marked NOT IMPLEMENTED or BLOCKED; none are claimed as working. Tests unavailable on the current platform are marked BLOCKED with reasons.
