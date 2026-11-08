# Integration Test Report — cvsz/autodj

**BLOCKED for real-mpv / real-Camfrog.** Integration tests run against mocks/fakes only in this Linux environment. Real mpv, yt-dlp network, TTS, and Camfrog are not available.

## Integration boundaries covered (mocked)

| Boundary | How tested | Files |
|----------|-----------|-------|
| GUI ↔ library | `load_folder` → `load_async` on executor; fake Tk | `test_gui_logic.py` |
| Library ↔ metadata extractor | `local_track` with mutagen (import-guarded) | `test_core.py`, `test_hardening.py` |
| Playlist ↔ playback engine | `PlaylistStore`, `load_playlist`, dedup, atomic save | `test_playlist_resolver.py`, `test_installer_data_safety.py` |
| Playback engine ↔ MPV | real CLI with **fake mpv** (`test_play_flow.py`) | `test_play_flow.py` |
| Console adapter ↔ core | stdin/stdout `!commands` EN+TH | `test_core.py`, `test_hardening.py` |
| Config ↔ runtime | `Config.load` validation + migration | `test_core.py`, `test_migration.py` |

## Tested scenarios

- Normal operation (queue, commands EN+TH, chat diff, parsing)
- Missing dependencies (yt_dlp/mutagen/pyttsx3 absent → graceful degradation)
- Invalid files / corrupted media → fallback, never crash
- Permission failures (log file, folder read) → logged, non-fatal
- Network interruption → yt-dlp failure path, module fallback
- Process termination → mpv stop/terminate/kill
- Application restart → playlist reload, config migration
- Duplicate events → dedup by source; echo suppression
- Concurrent actions → executor + RLock; rate-limit sliding window
- Cleanup after failures → temp log removal, thread join timeouts

## Not tested here (BLOCKED / NOT APPLICABLE)

- Real Camfrog UI Automation (no Camfrog; no authorized room)
- Real mpv / yt-dlp playback (fake mpv only)
- TTS audio output (pyttsx3 Windows-only)
- Windows launch / URI handling
- `build.ps1` / NSIS installer runtime

## Conclusion

Integration boundaries are verified against mocks/fakes. Mocks alone do not prove integration correctness with real mpv/Camfrog; those are BLOCKED and honestly classified.
