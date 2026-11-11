# Windows Build Review — CamfrogAutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`  
**Status:** ✅ VERIFIED on Windows 11 host — evidence `evidence/validation-evidence-20261111-175639.json` (5 passed, 0 failed, 0 skipped)

## Build artifacts reviewed

| Artifact | Purpose | Status |
|----------|---------|--------|
| `build.ps1` | PyInstaller build + sign + smoke test | ✅ Verified |
| `AutoDJ.spec` | PyInstaller spec mirroring build.ps1 | ✅ Verified |
| `build_exe.bat` / `build_installer.bat` | Batch wrappers for build.ps1 | ✅ Verified |
| `installer.nsi` | NSIS installer script | ✅ Verified |
| `scripts/build_installer.ps1` | NSIS installer builder (PowerShell) | ✅ Verified |
| `scripts/build_installer_linux.sh` | NSIS builder for Linux/WSL | Reviewed (syntax valid) |
| `scripts/build-all-hybrid.ps1` | Hybrid Windows→WSL workflow | Reviewed |
| `tools/check_build_env.py` | Verifies required packages before build | ✅ Verified |
| `app.ico`, `version_info.txt` | Icon + version metadata | Present |

## build.ps1 findings

- Verifies required packages (`yt-dlp`, `mutagen`, `pyttsx3`, `pywinauto`, ...) via `tools/check_build_env.py` before building — prevents an exe that starts but fails at runtime with `No module named 'yt_dlp'`.
- Builds `--onefile --noupx --windowed` with `--collect-all yt_dlp`, `--collect-submodules camfrog_autodj/pywinauto/pyttsx3`, hidden imports `comtypes`, `pyperclip`, `mutagen`.
- Copies `config.toml` (production config) → `dist/config.toml` (writable) and `mpv/` → `dist/mpv/` (mpv.exe + yt-dlp.exe).
- Smoke-tests `dist\AutoDJ.exe --version`; kills leftover processes.
- Signing: Pfx / Thumbprint / self-signed cert; RFC 3161 timestamping; `Get-AuthenticodeSignature` verification. Self-signed cert trusted on local machine via `cert\autodj-codesign.cer`.

## Windows signing (VERIFIED)

- GPG signing configured locally (commit.gpgsign=true, gpg.program).
- **Authenticode signature of dist\AutoDJ.exe verified** — signature status: Valid, signer CN=ZEAZDEV COMPANY LIMITED, O=ZEAZDEV COMPANY LIMITED, C=TH, timestamp DigiCert SHA256 RSA4096 Timestamp Responder 2026.
- NSIS installer signed successfully — `dist\Camfrog-AutoDJ-Setup-0.3.0.exe` (117.6 MB).

## Installer (installer.nsi) findings

- Per-user install to `$APPDATA\CamfrogAutoDJ` (`RequestExecutionLevel user`).
- Preserves existing `config.toml` on upgrade (`IfFileExists ... config_exists` skips overwriting).
- Uninstaller deletes only app-owned files; keeps `config.toml`, `playlist.json`, logs, playlists.
- `SEC_MPV` (mpv + yt-dlp) and `SEC_VBCABLE` (driver) are optional components (`/o`).
- Registry entries under HKCU for Add/Remove Programs and App Paths.
- Thai installer language requires `thai.nlf` on the makensis machine (documented in-file).

## Windows Runtime Validation (VERIFIED)

| Item | Status | Detail |
|------|--------|--------|
| Windows Installer Build | ✅ PASS | AutoDJ.exe + installer built successfully (117.6 MB) |
| Code Signing | ✅ PASS | Authenticode signature Valid, cert ZEAZDEV COMPANY LIMITED |
| UIA Adapter Runtime | ✅ PASS | UIA adapter attached to Camfrog room "ZeaZDev" |
| TTS Runtime | ✅ PASS | TTS SAPI available, 2 voices, WAV created |
| E2E Integration | ✅ PASS | All E2E prerequisites met |

Evidence: `evidence/validation-evidence-20261111-175639.json`
