# Penetration Test Report — Camfrog AutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`  
**Scope:** Application source + configuration + build/installer (static review); no live network or Camfrog target available  
**Status:** Reviewed; no live penetration test performed

## Approach

No authorized live target (Camfrog server, YouTube, mpv network) is available on this host, so no active/network penetration test was executed. The assessment is a static security review of trust boundaries, input validation, authorization, subprocess handling, and secret handling (see docs/audit/security-assessment.md).

## Trust boundaries reviewed

1. **config.toml (operator input):** validated by `config.py` (types, ranges, choices, regexes); unknown keys rejected with "did you mean" hint. Path traversal not applicable — music_dirs paths are used for scanning only, `resolve_executable` anchors relative paths to the application directory and `resolve_executable` refuses non-existent explicit paths.
2. **Chat input (room):** nickname-based authorization (documented spoofable); rate limit + cooldown per user; non-admin YouTube host restrictions; `clean_text` strips control characters before anything is typed into the room.
3. **Playlist file:** entries validated; corrupt file backed up, never silently deleted.
4. **Subprocess:** argument lists only (`shell=False` never used); `CREATE_NO_WINDOW` on Windows; timeouts on yt-dlp/mpv/TTS subprocesses.
5. **mpv IPC:** named pipe/socket per process; cleaned up after playback.

## Findings

No exploitable vulnerabilities identified in static review. The highest-risk item (nickname-based admin spoofing) is an inherent protocol limitation, documented in-code and in SECURITY.md-adjacent documentation; mitigated by fail-closed empty admin list.

## Not performed (no live target)

- Network penetration testing against YouTube/mpv.
- Live Camfrog UI Automation bypass testing.
- Fuzzing of yt-dlp/mpv subprocess inputs.
- Authenticode signature verification (no signing host).
