# Residual Risks — CamfrogAutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`

## Unmitigated risks (documented, not concealed)

| Risk | Location | Severity | Mitigation / status |
|------|----------|----------|---------------------|
| Nickname-based admin authorization is spoofable | `commands.py:Router.is_admin` | Medium | Documented in-code; fail-closed when `admins` empty; immutable account IDs not available in Camfrog chat protocol |
| GUI `position()` mpv IPC read can block on unresponsive mpv (Windows) | `player.py:_cmd_get` → `engine.py:position()` | Low | `open()` failure returns `None`; only live-but-unresponsive mpv is a risk; Windows-only, BLOCKED from validation |
| Live/unknown-duration stream stalls player loop | `player.py:_wait_for_mpv_end` | Low | Intentional ("live = no limit"); `mpv_timeout` bounds known-duration tracks |
| Settings dialog manually re-serializes config.toml | `gui.py:save_settings` | Low | Re-validates via `_validate`; re-reads config after save; drift risk for new keys |
| Self-signed code-signing cert only trusted where `.cer` imported | `build.ps1` | Medium | Documented; real OV/EV cert needed for public distribution |
| VBCable driver install requires Administrator | `installer.nsi` SEC_VBCABLE | Low | Documented; optional component |
| No real Camfrog / mpv / yt-dlp integration evidence | N/A | High | Classified NOT IMPLEMENTED; mocks do not prove live integration |
| GPG signing unavailable | git config | High (process) | Blocker; no signed commits produced |
| Windows build/installer unverified | build.ps1 / installer.nsi | High (process) | BLOCKED; not claimed as passing |

## Risks explicitly NOT claimed

- No claim of a valid Authenticode signature (no signing host).
- No claim of a successful Windows installer run (no Windows host).
- No claim of real Camfrog integration (no authorized test environment).
- No claim of real audio playback with mpv/yt-dlp (no real media on host).
