# AutoDJ Windows Installer and Uninstaller Acceptance

**Repository:** `cvsz/autodj`  
**Base Commit SHA (`main`):** `6baa8b7fcc47544eb21e3430e9f9db0124df81c6`  
**Date:** 2026-11-02  
**Auditor:** ZEAZDEV Super Ultra AI ORC  
**Verification Status:** PARTIALLY VERIFIED — NSIS uninstaller data-safety fix verified by unit tests; PowerShell installer backup/restore logic code-reviewed but not executable on Linux  

---

## 1. Executive Summary

A critical bug was discovered and fixed in the NSIS installer uninstaller: `RMDir "$INSTDIR"` deleted all remaining files including user data (config.toml, playlist.json, logs) despite the comment claiming to preserve them. This was fixed in PR #84. PowerShell installer scripts (`install.ps1`, `install-full-auto.ps1`) implement staging-based backup/restore before directory removal, but cannot be executed on Linux.

**This gate is PARTIALLY VERIFIED — NSIS uninstaller fix confirmed by unit tests; PowerShell installer backup/restore logic requires Windows execution for full validation.**

---

## 2. NSIS Installer (`installer.nsi`)

### 2.1 Uninstaller Data Safety Fix

**Bug:** `RMDir "$INSTDIR"` at line 272 deleted the entire installation directory including user data.

**Fix:** Removed `RMDir "$INSTDIR"`. The uninstaller now removes only application-owned files and subdirectories:

| Removed | Preserved |
|---------|-----------|
| `AutoDJ.exe` | `config.toml` |
| `app.ico` | `playlist.json` |
| `README.md` | `*.log` |
| `CHANGELOG.md` | `playlist_dir/*.json` |
| `LICENSE` | Unknown user files |
| `run_autodj.py` | |
| `install.ps1`, `install.bat` | |
| `uninstall.exe` | |
| `mpv\` directory | |
| `docs\` directory | |
| `tools\` directory | |

### 2.2 Installer Components

| Section | Components | Status |
|---------|-----------|--------|
| SEC_MAIN | AutoDJ.exe, app.ico, README.md, CHANGELOG.md, LICENSE, config.toml (conditional), run_autodj.py | Defined |
| SEC_MPV | mpv.exe, mpv.com, yt-dlp.exe, register/unregister bat, \_internal | Defined |
| SEC_VBCABLE | VBCABLE driver files | Optional |
| SEC_DOCS | docs/*.md | Optional |
| SEC_TOOLS | tools/*.py, *.ps1, *.sh | Optional |
| SEC_SCRIPTS | install.ps1, install.bat | Defined |

### 2.3 Installer Logic

| Feature | Implementation | Status |
|---------|---------------|--------|
| Per-user install dir | `$APPDATA\CamfrogAutoDJ` | Defined |
| No admin rights required | `RequestExecutionLevel user` | Defined |
| Windows 64-bit check | `.onInit` function | Defined |
| In-place upgrade | Previous uninstaller not invoked | Defined |
| Config preservation | `IfFileExists "$INSTDIR\config.toml" config_exists` | Defined |
| User data on uninstall | Files removed individually, not bulk RMDir | Fixed |

---

## 3. PowerShell Installer (`install.ps1`)

### 3.1 Backup/Restore Functions

| Function | Purpose | Status |
|----------|---------|--------|
| `Backup-UserData` | Backs up config.toml, playlist.json, *.log, playlist_dir/*.json to %TEMP% before removal | Code reviewed |
| `Restore-UserData` | Restores backed-up files after cloning | Code reviewed |
| Backup abort | Aborts installation if backup fails | Code reviewed |

### 3.2 Installation Flow

| Step | Function | Status |
|------|----------|--------|
| Windows 11 check | `Check-Windows11` | Code reviewed |
| Python check/install | `Check-Python` / `Install-Python` | Code reviewed |
| mpv check/install | `Check-Mpv` / `Install-Mpv` | Code reviewed |
| yt-dlp check/install | `Check-YtDlp` / `Install-YtDlp` | Code reviewed |
| VB-Cable check/install | `Check-VBCable` / `Install-VBCable` | Code reviewed |
| Project setup | `Setup-Project` | Code reviewed |
| Python deps | `Install-PythonDeps` | Code reviewed |
| Build | `Build-Exe` | Code reviewed |
| Config | `Create-Config` | Code reviewed |
| Shortcuts | `Create-Shortcuts` | Code reviewed |
| Auto-start | `Create-AutoStart` | Code reviewed |
| Uninstaller | `Create-Uninstaller` | Code reviewed |
| Verification | `Run-Verification` | Code reviewed |

---

## 4. Regression Tests (`tests/test_installer_data_safety.py`)

| Test | Description | Status |
|------|-------------|--------|
| `test_installer_preserves_existing_user_config_on_upgrade` | NSIS preserves config.toml on upgrade | PASSED |
| `test_uninstaller_removes_only_application_owned_files` | Uninstaller removes app files only, preserves user data | PASSED |

**Test assertions:**
- `'RMDir /r "$INSTDIR"' not in uninstall` — No recursive directory removal
- `'RMDir "$INSTDIR"' not in uninstall` — No directory removal that deletes user data
- `'Delete "$INSTDIR\\AutoDJ.exe"' in uninstall` — App-owned exe removed
- `'Delete "$INSTDIR\\config.toml"' not in uninstall` — User config preserved
- `'Delete "$INSTDIR\\playlist.json"' not in uninstall` — User playlist preserved

---

## 5. Blocker Status

**Status: PARTIALLY VERIFIED**

| Validation | Status | Reason |
|------------|--------|--------|
| NSIS uninstaller preserves user data | VERIFIED | Unit tests pass |
| NSIS config.toml preservation | VERIFIED | Unit tests pass |
| PowerShell backup/restore logic | NOT EXECUTABLE | Linux environment cannot run .ps1 |
| Fresh installation on Windows | NOT EXECUTABLE | No Windows host |
| Upgrade with existing user data | NOT EXECUTABLE | No Windows host |
| Rollback after failed upgrade | NOT EXECUTABLE | No Windows host |
| Uninstallation preserving user data | NOT EXECUTABLE | No Windows host |

---

## 6. Remaining Gaps

| Gap | Severity | Required Action |
|-----|----------|-----------------|
| No root/system path rejection | Medium | Add path validation to reject `C:\`, `C:\Windows`, etc. |
| No reparse point / symlink protection | Medium | Add symlink detection before directory operations |
| No corrupt backup detection | Low | Add backup integrity verification |
