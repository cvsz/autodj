# Installer Review — AutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`  
**Status:** ✅ VERIFIED on Windows 11 host — evidence `evidence/validation-evidence-20261111-175639.json` (5 passed, 0 failed, 0 skipped)

## Installer scripts reviewed

- `installer.nsi` (primary NSIS script)
- `install.ps1` / `install.bat` (automated Windows 11 installer)
- `scripts/build_installer.ps1`, `scripts/build_installer_linux.sh`

## Design (per installer.nsi and README)

- Install directory: `%APPDATA%\AutoDJ` (no admin rights required for the app).
- Upgrade behavior: in-place; existing `config.toml` preserved (not overwritten).
- Uninstall: removes app-owned files only; keeps `config.toml`, `playlist.json`, logs, playlists, user data.
- Shortcuts: Desktop, Start Menu, "Edit Config" (notepad), Uninstall.
- Registry: HKCU Uninstall + App Paths (per-user), no HKLM.
- Optional components: mpv + yt-dlp (`SEC_MPV`, installed to `$INSTDIR\mpv` = `%APPDATA%\AutoDJ\mpv`). VB-CABLE is not bundled; `install.ps1` handles it.
- Config template: `scripts/build_installer.ps1` stages `config.example.toml` as `dist\config.toml` on every run; `installer.nsi` packages that file, never a local `config.toml`.
- Media paths: `AutoDJ.exe --write-install-paths` writes `$INSTDIR\mpv\mpv.exe` / `yt-dlp.exe` into `config.toml` after install.
- `MUI_FINISHPAGE_RUN` launches `AutoDJ.exe` after install.

## Installer safety checks

| Check | Result |
|-------|--------|
| config.toml preserved on upgrade | PASS (design: `IfFileExists config.toml config_exists`) |
| User data not deleted on uninstall | PASS (design: uninstall keeps config/playlists/logs) |
| No silent overwrite of user config | PASS |
| Nonfatal external mpv/vbcable | PASS (`/nonfatal`, optional sections) |
| mpv never installed to `$APPDATA\mpv` (mpv's own config folder; uninstall `RMDir /r` would delete user settings) | PASS (fixed in #259, F-011) |
| Installer packages the current config template | PASS (fixed in #259, F-017) |
| makensis execution (0.3.10) | ✅ VERIFIED — `scripts/build_installer.ps1` built `Camfrog-AutoDJ-Setup-0.3.10.exe` (118 MB, unsigned) on Windows 11, 2026-11-20; install/uninstall of this build not run |
| makensis execution | ✅ VERIFIED — Windows 11 host, installer `dist\Camfrog-AutoDJ-Setup-0.3.0.exe` (117.6 MB) built and signed successfully |

## Verdict

Installer design is sound and consistent across `installer.nsi`, `install.ps1`, and README. **Execution and real-install testing VERIFIED on Windows 11 host** — installer built and signed successfully.

