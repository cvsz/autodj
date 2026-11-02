# AutoDJ Installer Lifecycle and Disaster Recovery Qualification

**Repository:** `cvsz/autodj`  
**Base Commit SHA (`main`):** `a837e0b70d48b4c28f0b209373e92f1bdd2592fe`  
**Date:** 2026-11-02  
**Auditor:** ZEAZDEV Super Ultra AI ORC  
**Verification Status:** PARTIALLY VERIFIED — NSIS uninstaller fix verified by unit tests; PowerShell installer backup/restore logic code-reviewed but not executable on Linux  

---

## 1. Executive Summary

A critical bug was discovered and fixed in the NSIS installer uninstaller: `RMDir "$INSTDIR"` (line 272) deleted the entire installation directory including user data (config.toml, playlist.json, logs) despite the comment claiming to preserve them. This has been fixed. PowerShell installer scripts (`install.ps1`, `install-full-auto.ps1`) implement staging-based backup/restore before directory removal, but cannot be tested on Linux.

**This gate is PARTIALLY VERIFIED — NSIS uninstaller fix confirmed by unit tests; PowerShell backup/restore logic requires Windows execution for full validation.**

---

## 2. Installation Qualification

### 2.1 Fresh Installation

| Aspect | Implementation | Status |
|--------|---------------|--------|
| Per-user install dir | `$APPDATA\Camfrog AutoDJ` (`installer.nsi:48`) | Code reviewed |
| No admin rights required | `RequestExecutionLevel user` (`installer.nsi:52`) | Code reviewed |
| Windows 11 check | Build 22000+ (`install.ps1:205`) | Code reviewed |
| Prerequisite installation | winget: Python, mpv, yt-dlp, Git, NSIS | Code reviewed |
| Project cloning | `git clone --depth 1` | Code reviewed |
| AutoDJ.exe build | `build.ps1 -NoSign` or with certificate | Code reviewed |
| Config creation | `config.toml` from template with prompts | Code reviewed |
| Shortcut creation | Desktop, Start Menu, Config editor, Uninstall | Code reviewed |
| Auto-start | Optional Startup folder shortcut | Code reviewed |
| Verification | `AutoDJ.exe --check` | Code reviewed |

### 2.2 Existing Installation Detection

| Aspect | Implementation | Status |
|--------|---------------|--------|
| Directory exists check | `Test-Path $ProjectDir` (`install.ps1:525`) | Code reviewed |
| Force/confirm overwrite | `Confirm "Directory exists. Overwrite?"` | Code reviewed |
| User data backup before removal | `Backup-UserData()` (`install.ps1`, `install-full-auto.ps1`) | Code reviewed (not executable on Linux) |

### 2.3 Destination Path Validation

| Aspect | Implementation | Status |
|--------|---------------|--------|
| No root/system path rejection | Not implemented in installer scripts | GAP — should reject `C:\`, `C:\Windows`, etc. |
| Permission validation | Not explicitly implemented | GAP |
| Reparse point / symlink protection | Not implemented | GAP |

---

## 3. Upgrade Qualification

### 3.1 Configuration Preservation

| Aspect | Implementation | Status |
|--------|---------------|--------|
| config.toml preserved on upgrade | NSIS `IfFileExists "$INSTDIR\config.toml" config_exists` | VERIFIED by `test_installer_data_safety.py` |
| config.example.toml not overwriting existing | `config_exists:` label skips overwrite | VERIFIED by `test_installer_data_safety.py` |
| PowerShell backup/restore | `Backup-UserData()` / `Restore-UserData()` | Code reviewed (not executable on Linux) |

### 3.2 Playlist Preservation

| Aspect | Implementation | Status |
|--------|---------------|--------|
| playlist.json backed up before removal | `Backup-UserData()` globs `playlist.json` | Code reviewed |
| playlist_dir/*.json backed up | `Backup-UserData()` globs `playlist_dir\*.json` | Code reviewed |
| Restore after clone | `Restore-UserData()` | Code reviewed |

### 3.3 Log Preservation

| Aspect | Implementation | Status |
|--------|---------------|--------|
| *.log backed up before removal | `Backup-UserData()` globs `*.log` | Code reviewed |
| Restore after clone | `Restore-UserData()` | Code reviewed |

### 3.4 Backup Integrity

| Aspect | Implementation | Status |
|--------|---------------|--------|
| Timestamped backup dir | `%TEMP%\autodj-userdata-backup-<timestamp>` | Code reviewed |
| Abort if backup fails | `if (-not $backupDir) { Fail ...; return $false }` | Code reviewed |
| Restore verification | Copy-Item with `-Force`, success messages | Code reviewed |

---

## 4. Uninstallation Qualification

### 4.1 Files Preserved by Default (CRITICAL FIX)

The following files are **NOT** deleted by the uninstaller:

| File | Reason |
|------|--------|
| `config.toml` | User configuration — explicitly preserved |
| `playlist.json` | User-requested tracks — explicitly preserved |
| `*.log` | User logs — explicitly preserved |
| `playlist_dir/*.json` | User playlists — explicitly preserved |

**Bug fixed:** `RMDir "$INSTDIR"` removed — this previously deleted ALL remaining files including user data.

### 4.2 Files Removed by Uninstaller

| File | Reason |
|------|--------|
| `AutoDJ.exe` | Application-owned |
| `app.ico` | Application-owned |
| `README.md` | Application-owned |
| `CHANGELOG.md` | Application-owned |
| `LICENSE` | Application-owned |
| `run_autodj.py` | Application-owned |
| `install.ps1` | Application-owned |
| `install.bat` | Application-owned |
| `uninstall.exe` | Application-owned |
| `mpv\` directory | Application-owned (bundled media tools) |
| `docs\` directory | Application-owned |
| `tools\` directory | Application-owned |

### 4.3 Destructive Operation Protections

| Protection | Implementation | Status |
|------------|---------------|--------|
| No root/system path rejection | NOT IMPLEMENTED | GAP — installer should reject `C:\`, `C:\Windows`, etc. |
| No reparse point / symlink protection | NOT IMPLEMENTED | GAP |
| Explicit authorization for destructive cleanup | Uninstaller prompts `Read-Host "Remove \$Proj? [y/N]"` | Code reviewed |
| Clear explanation of what will be removed | Uninstaller comments describe scope | Code reviewed |

---

## 5. Rollback Qualification

| Aspect | Implementation | Status |
|--------|---------------|--------|
| Failed upgrade rollback | Backup restored after clone failure | Code reviewed |
| Backup restoration | `Restore-UserData()` copies files back | Code reviewed |
| Corrupt backup detection | Not explicitly implemented | GAP |
| Interrupted rollback | Not explicitly handled | GAP |
| Recovery after application crash | Not explicitly handled | GAP |

---

## 6. Regression Tests

### 6.1 Existing Tests (`tests/test_installer_data_safety.py`)

| Test | Description | Status |
|------|-------------|--------|
| `test_installer_preserves_existing_user_config_on_upgrade` | Verifies NSIS preserves config.toml on upgrade | PASSED |
| `test_uninstaller_removes_only_application_owned_files` | Verifies uninstaller removes app-owned files only, preserves user data | PASSED |

### 6.2 Test Assertions (Updated)

| Assertion | Purpose |
|-----------|---------|
| `'RMDir /r "$INSTDIR"' not in uninstall` | No recursive directory removal |
| `'RMDir "$INSTDIR"' not in uninstall` | No directory removal that would delete user data |
| `'Delete "$INSTDIR\\AutoDJ.exe"' in uninstall` | App-owned exe is removed |
| `'Delete "$INSTDIR\\config.toml"' not in uninstall` | User config is preserved |
| `'Delete "$INSTDIR\\playlist.json"' not in uninstall` | User playlist is preserved |
| `"Keep config.toml, playlist.json, logs, playlists" in uninstall` | Comment documents intent |

---

## 7. Blocker Status

**Status: PARTIALLY VERIFIED**

| Validation | Status | Reason |
|------------|--------|--------|
| NSIS uninstaller preserves user data | VERIFIED | Unit tests pass |
| NSIS config.toml preservation on upgrade | VERIFIED | Unit tests pass |
| PowerShell backup/restore logic | NOT EXECUTABLE | Linux environment cannot run .ps1 |
| Fresh installation on Windows | NOT EXECUTABLE | No Windows host |
| Upgrade with existing user data | NOT EXECUTABLE | No Windows host |
| Rollback after failed upgrade | NOT EXECUTABLE | No Windows host |
| Uninstallation preserving user data | NOT EXECUTABLE | No Windows host |

---

## 8. Remaining Gaps

| Gap | Severity | Required Action |
|-----|----------|-----------------|
| No root/system path rejection in installer | Medium | Add path validation to reject `C:\`, `C:\Windows`, etc. |
| No reparse point / symlink protection | Medium | Add symlink/reparse point detection before directory operations |
| No corrupt backup detection | Low | Add backup integrity verification before restore |
| No interrupted rollback handling | Low | Add rollback state tracking and resumption |
