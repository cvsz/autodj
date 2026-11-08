# Residual Risks — cvsz/autodj

Risks that remain after this audit. Each is documented with classification; none are concealed as "zero error."

## Environment limitations (BLOCKED, not defects)

- Windows PyInstaller build and NSIS installer not executed here (`pwsh`/Windows absent).
- NSIS installer artifacts present in `dist/` are pre-existing; signatures not verified.
- Real mpv / yt-dlp playback not exercised (fake mpv in tests).
- Real Camfrog UI Automation not tested (no Camfrog; no authorized room).
- TTS (pyttsx3) not testable (Windows SAPI-only).
- Code signing with a real (OV/EV) certificate not configured; self-signed cert trusted only locally after `.cer` import.
- `policedbc` independent review and `cvsz` merge not yet executed (PR pending).

## Documented design risks (not defects; operator must accept)

| Risk | Mitigation |
|------|-----------|
| Nickname-based admin auth is spoofable on Camfrog | Fail-closed: empty `admins` → no admin access; operator sets real nicks; documented in `commands.py` |
| UIA chat depends on Camfrog window/control indexes; `line_regex` per Camfrog version | `--discover` tunes config; documented caveat in README |
| Background chat send cannot prove page acceptance | `send_mode=auto` verifies appearance; `foreground` fallback |
| No persisted queue/volume/shuffle across restart | `playlist.json` persists requests; runtime state reset by design (documented) |
| `MpvPlayer._cmd_get` Windows named-pipe read has no read timeout | GUI poll is 500 ms; returns None on failure; Windows-only residual |
| Long Windows paths (`\\?\` prefix not applied) | `Path` handles most; very long paths may need operator attention |
| Self-signed code signing → SmartScreen warnings on public distribution | Use real OV/EV cert or Azure Trusted Signing via `-Pfx` |

## No defects concealed

No `|| echo warning`, no silently swallowed lint failures, no assumed Windows passes from Linux syntax checks, no fake test-equivalence claims. All blocked checks are explicitly BLOCKED/NOT APPLICABLE.
