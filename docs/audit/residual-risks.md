# Residual Risks — CamfrogAutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`

## Unmitigated risks (documented, not concealed)

| Risk | Location | Severity | Mitigation / status |
|------|----------|----------|---------------------|
| Nickname-based admin authorization is spoofable | `commands.py:Router.is_admin` | Medium | Documented in-code; fail-closed when `admins` empty; immutable account IDs not available in Camfrog chat protocol |
| GUI `position()` mpv IPC read can block on unresponsive mpv (Windows) | `player.py:_cmd_get` → `engine.py:position()` | Low | `open()` failure returns `None`; only live-but-unresponsive mpv is a risk; Windows-only, VERIFIED on Windows 11 host |
| Self-signed code-signing cert only trusted where `.cer` imported | `build.ps1` | Medium | Documented; real OV/EV cert needed for public distribution |
| Mic greeting detection unverified against a live Camfrog room | `engine.py:_mic_notice_nick` | Low | Whole-line + sender match only; if real notices use other wording or another sender, the greeting silently does not fire |
| A user can still self-announce as DJ by typing `<own nick> is now speaking` | `engine.py:_mic_notice_nick` | Low | Bounded by `mic_greeting_cooldown` (300 s) per nick; cannot name another user |
| Upgrades from a 0.3.10 build leave the old `%APPDATA%\mpv` copy | `installer.nsi` | Low | Not deleted on purpose (may hold the user's own mpv config); config is repointed by `--write-install-paths` |
| VBCable driver install requires Administrator | `installer.nsi` SEC_VBCABLE | Low | Documented; optional component |
| No real Camfrog / mpv / yt-dlp integration evidence | N/A | High | Classified NOT IMPLEMENTED; mocks do not prove live integration |
| GPG signing unavailable | git config | High (process) | Blocker; no signed commits produced |
| Windows build/installer unverified | build.ps1 / installer.nsi | High (process) | VERIFIED on Windows 11 host — evidence `evidence/validation-evidence-20261111-175639.json` (5 passed, 0 failed, 0 skipped) |

## Risks explicitly NOT claimed

- No claim of real Camfrog integration (no authorized test environment).
- No claim of real audio playback with mpv/yt-dlp (no real media on host).
