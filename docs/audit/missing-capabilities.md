# Missing Capabilities — cvsz/autodj

Capability gaps classified per the ZEAZ evidence decision rule. Items marked NOT IMPLEMENTED are genuine gaps (not bugs). Items marked NOT APPLICABLE / BLOCKED cannot be verified in this Linux environment (no Windows, no `pwsh`, no real Camfrog/mpv).

## NOT IMPLEMENTED (genuine gaps)

- **Persisted queue/volume/shuffle across restart.** `playlist.json` persists user requests; the in-memory queue, volume, shuffle, and repeat state reset on restart. Documented by design (O8 in AUDIT.md); not a regression.
- **Real Camfrog end-to-end integration.** Chat read/send uses UI Automation (`adapters/uia.py`); tested with mocks/fakes only. No real Camfrog test environment available here. Classification: do not claim live Camfrog integration works.
- **Real mpv / yt-dlp playback.** `tests/test_play_flow.py` runs the real CLI with a **fake mpv**. Actual mpv/yt-dlp playback is not exercised in this environment.
- **TTS (pyttsx3) audio output.** pyttsx3 is Windows SAPI-only; not installable/testable here. `--check` reports it as WARN if absent.
- **Windows code signing with a real certificate.** `build.ps1` creates/reuses a self-signed cert (trusted only locally after `.cer` import). No OV/EV certificate or Azure Trusted Signing configured here. Public distribution would produce SmartScreen warnings.

## NOT APPLICABLE / BLOCKED (environment-limited)

| Capability | State | Reason |
|------------|-------|--------|
| PyInstaller Windows `.exe` build (`build.ps1`) | BLOCKED | Windows PowerShell only; `pwsh` not available on Linux |
| NSIS installer build (`installer.nsi`, `makensis`) | BLOCKED | Windows only |
| `install.ps1` / `install.bat` automated Windows 11 installer | BLOCKED | Windows 11 only |
| PowerShell script execution / Pester | BLOCKED | `pwsh`/`powershell` not installed |
| `build.ps1` code signing + signature verification | BLOCKED | Windows only; no code-signing cert present |
| Real Camfrog UI Automation integration test | BLOCKED | No Camfrog installed; no authorized test room |
| `AutoDJ.exe --gui` / `--check` / `--say` on Windows | BLOCKED | Windows-only frozen exe not buildable here |
| `make build` / `make installer` / `make nsiswindows11` | BLOCKED | Windows targets |
| `mutation-smoke` (`tools/mutate.sh`) | NOT APPLICABLE | `tools/mutate.sh` not present in repo |

## What IS verified (Linux)

- Python 3.11+ runtime, CLI, console mode
- All 325 pytest tests
- Ruff lint + format, mypy
- ShellCheck + `bash -n` on all `.sh` scripts
- GPG commit signing (key `515DB3BD...9D872`, `cvsz <seaza@msn.com>`)
- `gh` authentication (`cvsz` active; `policedbc` available)
- TOML/JSON/YAML validity
- Secret scan (none tracked)
- `scripts/validate_repo.py`
