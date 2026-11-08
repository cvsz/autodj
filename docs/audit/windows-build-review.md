# Windows Build Review — Camfrog AutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`  
**Status:** BLOCKED — no Windows host available

## Build artifacts reviewed (source only, not executed)

| Artifact | Purpose | Status |
|----------|---------|--------|
| `build.ps1` | PyInstaller build + sign + smoke test | Reviewed; not executed |
| `AutoDJ.spec` | PyInstaller spec mirroring build.ps1 | Reviewed |
| `build_exe.bat` / `build_installer.bat` | Batch wrappers for build.ps1 | Reviewed |
| `installer.nsi` | NSIS installer script | Reviewed |
| `scripts/build_installer.ps1` | NSIS installer builder (PowerShell) | Reviewed |
| `scripts/build_installer_linux.sh` | NSIS builder for Linux/WSL | Reviewed |
| `scripts/build-all-hybrid.ps1` | Hybrid Windows→WSL workflow | Reviewed |
| `tools/check_build_env.py` | Verifies required packages before build | Reviewed |
| `app.ico`, `version_info.txt` | Icon + version metadata | Present |

## build.ps1 findings

- Verifies required packages (`yt-dlp`, `mutagen`, `pyttsx3`, `pywinauto`, ...) via `tools/check_build_env.py` before building — prevents an exe that starts but fails at runtime with `No module named 'yt_dlp'`.
- Builds `--onefile --noupx --windowed` with `--collect-all yt_dlp`, `--collect-submodules camfrog_autodj/pywinauto/pyttsx3`, hidden imports `comtypes`, `pyperclip`, `mutagen`.
- Copies `config.example.toml` → `dist/config.toml` (writable) and `mpv/` → `dist/mpv/` (mpv.exe + yt-dlp.exe).
- Smoke-tests `dist\AutoDJ.exe --version`; kills leftover processes.
- Signing: Pfx / Thumbprint / self-signed cert; RFC 3161 timestamping; `Get-AuthenticodeSignature` verification. Self-signed cert trusted on local machine via `cert\autodj-codesign.cer`.

## Windows signing (NOT verified)

- `commit.gpgsign = true` and `gpg.program` configured locally, but signing requires `GPG_PASSPHRASE` (unset) and no TTY → BLOCKED.
- Authenticode signature of `dist\AutoDJ.exe` / installer could not be verified. **Not claimed as signed.**

## Installer (installer.nsi) findings

- Per-user install to `$APPDATA\Camfrog AutoDJ` (`RequestExecutionLevel user`).
- Preserves existing `config.toml` on upgrade (`IfFileExists ... config_exists` skips overwriting).
- Uninstaller deletes only app-owned files; keeps `config.toml`, `playlist.json`, logs, playlists.
- `SEC_MPV` (mpv + yt-dlp) and `SEC_VBCABLE` (driver) are optional components (`/o`).
- Registry entries under HKCU for Add/Remove Programs and App Paths.
- Thai installer language requires `thai.nlf` on the makensis machine (documented in-file).

## Verdict

Windows build and installer behavior **cannot be verified on this Linux host**. All Windows build claims are BLOCKED, not assumed. A `make build` / `make installer` / `makensis` run on Windows 11 with NSIS is required to close this gate.
