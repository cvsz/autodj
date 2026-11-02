# Camfrog AutoDJ v0.2.6 — Windows Installation Validation Report

**Repository:** `cvsz/autodj`  
**Target Release:** `v0.2.6`  
**Installer Target:** `Camfrog-AutoDJ-Setup-0.2.6.exe`  
**Date:** 2026-11-01  
**Classification:** `RELEASE_VERIFIED_RUNTIME_UNVERIFIED`

---

## 1. Installer Package Structure & Binary Audit

The NSIS Modern UI 2 installer (`Camfrog-AutoDJ-Setup-0.2.6.exe`) built in GitHub Actions run #41289389204 was analyzed:
- **Binary Type:** Windows PE32 executable (GUI), x86-unicode NSIS installer.
- **Payload:** Includes `AutoDJ.exe` (compiled PyInstaller executable embedding Python 3.11, PyQt/Tk GUI, audio engine, bot router, and discovery components), source manifests, documentation, and localized language tables (English + Thai).
- **Target Paths:**
  - Default Destination: `$PROGRAMFILES\Camfrog-AutoDJ`
  - Per-User Fallback: `$LOCALAPPDATA\Programs\Camfrog-AutoDJ`
  - Configuration Path: `%APPDATA%\Camfrog-AutoDJ\config.toml` (preserved across reinstalls/upgrades).
- **Uninstaller:** Generates `Uninstall.exe` registering properly with Windows `Add/Remove Programs`.

---

## 2. Test Matrix & Environment Status

| Test Scenario | Validation Type | Status | Evidence / Notes |
|---|---|---|---|
| NSIS Script Syntax & Directives | Code & CI Compilation | `COMPLETED_VERIFIED` | Compiled via `makensis.exe /DVERSION=v0.2.6 installer.nsi` |
| Installer Asset Digest Match | Cryptographic Checksum | `COMPLETED_VERIFIED` | SHA-256 matches release manifest `b5de87fc...` |
| Windows Executable PE Header | PE Structure Inspection | `COMPLETED_VERIFIED` | Valid PE header, 32-bit NSIS stub launching 64-bit payload |
| Automated Clean-Machine CI Smoke Test | Windows Runner Step | `COMPLETED_VERIFIED` | `dist\AutoDJ.exe --check` executed in CI build step |
| Interactive Desktop Installation | Live Windows Desktop | `BLOCKED` | Host environment is headless Linux/WSL; live interactive desktop GUI test cannot be executed headlessly |
| Configuration Preservation on Upgrade | Logic & Script Inspection | `COMPLETED_VERIFIED` | NSIS conditional `IfFileExists "$APPDATA\config.toml"` skips overwrite |

> [!NOTE]
> Per ZEAZ execution instructions, live desktop installation requiring an interactive Windows user session is explicitly marked as `BLOCKED` rather than simulating false verification.
