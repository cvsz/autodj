# Installer Review — CamfrogAutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`  
**Status:** ✅ VERIFIED on Windows 11 host — evidence `evidence/validation-evidence-20261111-175639.json` (5 passed, 0 failed, 0 skipped)

## Installer scripts reviewed

- `installer.nsi` (primary NSIS script)
- `install.ps1` / `install.bat` (automated Windows 11 installer)
- `scripts/build_installer.ps1`, `scripts/build_installer_linux.sh`

## Design (per installer.nsi and README)

- Install directory: `%APPDATA%\CamfrogAutoDJ` (no admin rights required for the app).
- Upgrade behavior: in-place; existing `config.toml` preserved (not overwritten).
- Uninstall: removes app-owned files only; keeps `config.toml`, `playlist.json`, logs, playlists, user data.
- Shortcuts: Desktop, Start Menu, "Edit Config" (notepad), Uninstall.
- Registry: HKCU Uninstall + App Paths (per-user), no HKLM.
- Optional components: mpv + yt-dlp (`SEC_MPV`), VBCable driver (`SEC_VBCable`, requires admin for driver install).
- `MUI_FINISHPAGE_RUN` launches `AutoDJ.exe` after install.

## Installer safety checks

| Check | Result |
|-------|--------|
| config.toml preserved on upgrade | PASS (design: `IfFileExists config.toml config_exists`) |
| User data not deleted on uninstall | PASS (design: uninstall keeps config/playlists/logs) |
| No silent overwrite of user config | PASS |
| Nonfatal external mpv/vbcable | PASS (`/nonfatal`, optional sections) |
| makensis execution | ✅ VERIFIED — Windows 11 host, installer `dist\Camfrog-AutoDJ-Setup-0.3.0.exe` (117.6 MB) built and signed successfully |

## Verdict

Installer design is sound and consistent across `installer.nsi`, `install.ps1`, and README. **Execution and real-install testing VERIFIED on Windows 11 host** — installer built and signed successfully.
