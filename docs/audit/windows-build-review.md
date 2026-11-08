# Windows Build Review — cvsz/autodj

**BLOCKED — Windows-only.** `build.ps1` requires Windows PowerShell; `pwsh`/`powershell` is not installed on this Linux host. `make build`/`make build-all`/`make sign` are Windows targets. No Windows build artifact was produced or signed here. Nothing is assumed.

## Build scripts audited (source inspection only)

- `build.ps1`: PyInstaller onefile build + code signing + smoke test. Verifies every required package is installed (`tools/check_build_env.py`) so the exe doesn't fail later with `No module named 'yt_dlp'`; builds `dist\AutoDJ.exe` with `app.ico` and `version_info.txt` (company ZEAZDEV COMPANY LIMITED); copies `config.toml`; signs the exe (SHA256 + timestamp); prints signature status and SHA256. `-Clean` wipes build/dist/spec; `-NoSign` builds only. Certificate: `-Pfx`/`-Password` (or `AUTODJ_PFX`/`AUTODJ_PFX_PASSWORD`), `-Thumbprint` (or `AUTODJ_CERT_THUMBPRINT`), else self-signed cert reused/created in user store. Writes `cert\autodj-codesign.cer`. No UPX. Exe smoke-tested with `--version`. `AutoDJ.spec` mirrors `build.ps1`. `camfrog_autodj/__init__.py` must contain only `__version__`.
- `build_exe.bat` / `build_installer.bat`: batch wrappers.
- `scripts/build_installer.ps1` / `build_installer_linux.sh` / `build-all-hybrid.ps1`: installer pipelines.
- `tools/check_build_env.py`: build-env verification.
- `tools/make_cert.ps1` / `tools/sign_exe.ps1`: cert/sign helpers.

## Verification items not executable here

| Item | State | Reason |
|------|-------|--------|
| PyInstaller hidden imports / package discovery | BLOCKED | needs Windows + pyinstaller |
| Data files / icons / runtime hooks | BLOCKED | needs Windows build |
| UPX policy (no UPX) | documented only | not verified by build |
| Reproducibility | BLOCKED | needs build |
| Startup behavior / missing DLLs | BLOCKED | needs Windows runtime |
| Code signing + signature verification | BLOCKED | no cert; `pwsh` absent |
| Self-signed cert trust | documented only | `.cer` import required per PC |

## Conclusion

Windows build is **documented and reviewed by source inspection but not executed.** BLOCKED in this environment. Must be validated on Windows with `pwsh`, PyInstaller, NSIS, and (for signing) a code-signing certificate before any release claim.
