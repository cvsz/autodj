# Camfrog AutoDJ - Automated Windows 11 Installer Specification

> **Single Source of Truth** for all installer-related logic, configuration, and build processes.

---

## 📋 Overview

Camfrog AutoDJ provides **two complementary installation paths**:

| Path | Use Case | Technology |
|------|----------|------------|
| **Interactive PowerShell Installer** (`install.ps1`) | End-user setup, development machines, CI/CD | PowerShell 5.1+ / 7+ |
| **NSIS Packaged Installer** (`installer.nsi`) | Distribution via GitHub Releases, offline installs | NSIS 3.08+ |

Both paths share the same **prerequisites, configuration, and verification logic**.

---

## 🎯 Prerequisites (Windows 11+)

### Required Runtime Dependencies

| Component | Minimum Version | Installation Method | Verification |
|-----------|----------------|---------------------|--------------|
| **Windows** | 11 (Build 22000+) | Pre-installed | `Get-CimInstance Win32_OperatingSystem` |
| **Python** | 3.11+ | winget (`Python.Python.3.11`), official installer, or Chocolatey | `python --version` |
| **mpv** | Latest | winget (`mpv.mpv`), Chocolatey, or manual | `mpv --version` |
| **yt-dlp** | Latest | winget (`yt-dlp.yt-dlp`), pip, or manual download | `yt-dlp --version` |
| **VB-Cable** | Driver Pack 43+ | Manual download (requires Admin) | `Get-PnpDevice -Class MEDIA` |

### Optional / Development
- **Git** - for cloning repo (winget: `Git.Git`)
- **NSIS** - for building installer (winget: `NSIS.NSIS`)
- **signtool** - for code signing (Windows SDK)

---

## 🔧 Installation Flow (Both Paths)

```
┌─────────────────────────────────────────────────────────────────┐
│                    INSTALLATION PIPELINE                        │
├─────────────────────────────────────────────────────────────────┤
│  1. VERIFY          → Windows 11 (build ≥ 22000)               │
│  2. CHECK DEPS      → Python, mpv, yt-dlp, VB-Cable            │
│  3. INSTALL DEPS    → winget / pip / manual download           │
│  4. SETUP PROJECT   → Clone repo or use existing directory     │
│  5. PYTHON DEPS     → pip install -e .[build,dev]              │
│  6. BUILD EXE       → PyInstaller (build.ps1)                  │
│  7. CREATE CONFIG   → Copy config.example.toml → config.toml   │
│  8. CREATE SHORTCUTS→ Desktop, Start Menu, Config, Uninstall   │
│  9. AUTO-START      → (Optional) Startup folder shortcut       │
│ 10. VERIFY          → AutoDJ.exe --check                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 File Structures

### Source Repository Layout (for NSIS packaging)
```
camfrog-autodj/
├── installer.nsi              # NSIS script (this spec)
├── install.ps1                # Interactive PowerShell installer
├── install.bat                # Batch wrapper for install.ps1
├── build.ps1                  # Build + sign AutoDJ.exe
├── build_installer.bat        # NSIS builder (Windows)
├── scripts/
│   ├── build_installer.ps1    # NSIS builder (PowerShell)
│   └── build_installer_linux.sh  # NSIS builder (Linux/Wine)
├── dist/                      # Build output (created by build.ps1)
│   ├── AutoDJ.exe             # Main executable
│   ├── app.ico                # Application icon
│   ├── config.example.toml    # Config template
│   ├── README.md
│   ├── CHANGELOG.md
│   ├── LICENSE.md
│   ├── install.ps1
│   ├── uninstall.ps1
│   └── run_autodj.py
├── camfrog_autodj/            # Python package
├── tools/                     # Build/dev tools
├── tests/                     # Test suite
└── docs/                      # Documentation
```

### Installed Layout (NSIS installer target)
```
%PROGRAMFILES64%\Camfrog AutoDJ\
├── AutoDJ.exe                 # Main executable
├── app.ico                    # Icon
├── config.toml                # User config (copied from example)
├── config.example.toml        # Template
├── README.md
├── CHANGELOG.md
├── LICENSE.md
├── run_autodj.py              # Entry point script
├── install.ps1                # Re-installer
├── uninstall.ps1              # Uninstaller
├── uninstall.exe              # NSIS uninstaller
├── docs\                      # Documentation (optional component)
├── src\                       # Python source (optional component)
├── tools\                     # Build tools (optional component)
└── tests\                     # Tests (optional component)
```

### Start Menu Shortcuts Created
```
Start Menu > Programs > Camfrog AutoDJ\
├── Camfrog AutoDJ.lnk         → AutoDJ.exe --gui
├── Edit Config.lnk            → notepad.exe config.toml
└── Uninstall.lnk              → uninstall.exe
```

### Desktop Shortcut
```
Desktop\Camfrog AutoDJ.lnk     → AutoDJ.exe --gui
```

### Registry (Add/Remove Programs)
```
HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\CamfrogAutoDJ
  DisplayName        = "Camfrog AutoDJ"
  DisplayVersion     = "0.2.3"
  Publisher          = "ZEAZDEV COMPANY LIMITED"
  URLInfoAbout       = "https://github.com/cvsz/autodj"
  InstallLocation    = "%PROGRAMFILES64%\Camfrog AutoDJ"
  UninstallString    = "%PROGRAMFILES64%\Camfrog AutoDJ\uninstall.exe"
  DisplayIcon        = "%PROGRAMFILES64%\Camfrog AutoDJ\app.ico"
  NoModify           = 1
  NoRepair           = 1
```

---

## ⚙️ Configuration

### config.toml (User Settings)
```toml
# Required - edit after install
bot_nick = "AutoDJ"
admins = ["YourCamfrogNick"]
music_dirs = ["D:/Music"]

# Audio (set after VB-Cable install)
# audio_device = "CABLE Output (VB-Audio Virtual Cable)"

# Optional
[camfrog]
room_name = ""
auto_join = false

[playback]
default_volume = 0.5
crossfade_seconds = 2

[youtube]
prefer_opus = true
```

### config.example.toml (Template)
Committed to repo - copied to `config.toml` on first install.

---

## 🏗️ Build Process

### 1. Build AutoDJ.exe (PyInstaller)
```powershell
# From project root
.\build.ps1              # Build + self-sign
.\build.ps1 -Clean       # Clean build
.\build.ps1 -NoSign      # Build only
.\build.ps1 -Pfx cert.pfx -Password "xxx"  # Sign with real cert
```

**PyInstaller spec (from build.ps1):**
- `--onefile` - Single executable
- `--noupx` - No UPX (fewer AV false positives)
- `--collect-all yt_dlp` - Include all yt-dlp extractors
- `--collect-submodules pywinauto, pyttsx3, camfrog_autodj`
- `--hidden-import comtypes, pyperclip, mutagen`
- `--version-file version_info.txt` - Embed version metadata
- `--icon app.ico` - Application icon

### 2. Build NSIS Installer
```powershell
# Windows
.\build_installer.bat

# PowerShell (cross-platform)
.\scripts\build_installer.ps1 -Version 0.2.3

# Linux/Wine
./scripts/build_installer_linux.sh 0.2.3
```

**Required files in `dist/` for NSIS:**
```
dist/
├── AutoDJ.exe
├── app.ico
├── config.example.toml
├── README.md
├── CHANGELOG.md
├── LICENSE.md
├── install.ps1
├── uninstall.ps1
└── run_autodj.py
```

---

## 🔐 Code Signing

### Self-Signed (Development)
- Created automatically by `build.ps1` if no cert found
- Stored in `cert/autodj-codesign.cer`
- Trusted on build machine via `Root` + `TrustedPublisher` stores

### Production (Real Certificate)
```powershell
# Build with purchased cert
.\build.ps1 -Pfx "cert.pfx" -Password "xxx"

# Or use cert in store
.\build.ps1 -Thumbprint "ABC123..."

# Sign installer separately
signtool sign /f cert.pfx /p "xxx" /t http://timestamp.digicert.com "Camfrog-AutoDJ-Setup-0.2.3.exe"
```

**Timestamp servers (tried in order):**
1. `http://timestamp.digicert.com`
2. `http://timestamp.sectigo.com`
3. `http://timestamp.globalsign.com/tsa/r6advanced1`

---

## ✅ Verification

### Post-Install Check (`AutoDJ.exe --check`)
```
[OK]   Windows 11 Build 22631
[OK]   Python 3.11.9
[OK]   mpv 2024.04.02
[OK]   yt-dlp 2024.07.04
[OK]   VB-Cable detected
[OK]   config.toml valid
[OK]   Music directory accessible
[OK]   Camfrog window detectable
```

### Manual Verification Commands
```powershell
# Check exe runs
.\AutoDJ.exe --version

# Full diagnostic
.\AutoDJ.exe --check -v

# Test GUI launch
.\AutoDJ.exe --gui
```

---

## 📜 Scripts Reference

### install.ps1 (Interactive Installer)
**Parameters:**
```powershell
.\install.ps1 [-ProjectDir <path>] [-NoBuild] [-NoShortcuts] [-AutoStart] [-PythonVersion <ver>] [-GitBranch <branch>] [-Verbose] [-Force] [-SkipVBCable]
```

**Key Functions:**
- `Check-Windows11` - Verifies build ≥ 22000
- `Check-Python/Mpv/YtDlp/VBCable` - Dependency detection
- `Install-Python/Mpv/YtDlp/VBCable` - Installation via winget/pip/manual
- `Setup-Project` - Git clone
- `Install-PythonDeps` - `pip install -e .[build,dev]`
- `Build-Exe` - Calls `build.ps1`
- `Create-Config` - Interactive config setup
- `Create-Shortcuts` - Desktop + Start Menu
- `Create-AutoStart` - Startup folder
- `Run-Verification` - `AutoDJ.exe --check`
- `Create-Uninstaller` - Generates `uninstall.ps1`

### install.bat (Wrapper)
```batch
@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
```
- Checks Windows 11 build number (fixed: `tokens=4` for `ver` output)
- Ensures PowerShell exists
- Passes all arguments to `install.ps1`

### installer.nsi (NSIS Script)
**Sections:**
- `SEC_MAIN` (Required) - Core files
- `SEC_DOCS` - Documentation
- `SEC_SRC` - Python source
- `SEC_TOOLS` - Build tools
- `SEC_TESTS` - Tests
- `SEC_SCRIPTS` - Install/uninstall scripts

**Key Macros:**
- `MUI2` - Modern UI 2 pages (Welcome, License, Components, Directory, Install, Finish)
- `LogicLib` - Conditional logic
- `FileFunc` - File operations
- `x64` - 64-bit enforcement

### build_installer.ps1 (NSIS Builder)
```powershell
.\scripts\build_installer.ps1 -Version 0.2.3 -SrcDir dist -OutDir dist [-Sign]
```
- Validates NSIS (`makensis`) in PATH
- Verifies required files in `dist/`
- Generates `installer.nsi` with version substitution
- Runs `makensis` with `/DVERSION`, `/DSRCDIR`, `/DOUTDIR`
- Optionally signs output installer

---

## 🐛 Known Issues & Fixes

| Issue | Fix |
|-------|-----|
| `ver` parsing in `install.bat` | Changed `tokens=3` → `tokens=4` + strip `]` |
| NSIS not found | Install NSIS 3.08+ and restart terminal |
| "not was unexpected" | Side effect of NSIS missing; install NSIS |
| Python not on PATH after install | `build.ps1` refreshes `$env:PATH` from registry |
| VB-Cable requires reboot | Installer warns; user must reboot |

---

## 🔄 Version Management

### Single Version Source
**`version_info.txt`** - Authoritative version for:
- PyInstaller `--version-file`
- NSIS `APP_VERSION`
- `build.ps1` default
- `build_installer.ps1` default

```txt
# version_info.txt
VSVersionInfo(
  ffi=FixedFileInfo(filevers=(0, 2, 3, 0), prodvers=(0, 2, 3, 0), ...)
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('FileVersion', '0.2.3.0'),
    StringStruct('ProductVersion', '0.2.3.0')
  ])])]
)
```

### Updating Version
1. Edit `version_info.txt` → `filevers=(0, 2, 4, 0)`, `prodvers=(0, 2, 4, 0)`, `FileVersion='0.2.4.0'`, `ProductVersion='0.2.4.0'`
2. Edit `installer.nsi` → `!define APP_VERSION "0.2.4"`
3. Edit `install.ps1` → Update version in header comment
4. Run `.\build.ps1 -Clean` then `.\build_installer.bat`

---

## 📦 Distribution Checklist

Before releasing `Camfrog-AutoDJ-Setup-{version}.exe`:

- [ ] `build.ps1 -Clean` passes
- [ ] `AutoDJ.exe --version` works
- [ ] `AutoDJ.exe --check` passes
- [ ] `build_installer.bat` produces installer
- [ ] Installer runs on clean VM (Windows 11)
- [ ] Installer creates shortcuts, registry entries
- [ ] Uninstaller removes all files + registry
- [ ] Installer signed with production cert (optional but recommended)
- [ ] SHA256 recorded for release notes

---

## 🛠️ Troubleshooting

### "NSIS not found"
```powershell
winget install NSIS.NSIS
# Restart terminal
```

### "Python not found after install"
```powershell
$env:PATH = [Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [Environment]::GetEnvironmentVariable("PATH", "User")
```

### "VB-Cable audio not working"
1. Install VB-Cable (run `install.ps1` as Admin or manual)
2. Reboot
3. Run `mpv --audio-device=help` to find device name
4. Set `audio_device` in `config.toml`

### "Access denied" signing
- Ensure `signtool` in PATH (Windows SDK)
- Run as Admin for cert store access
- Check cert has Code Signing EKU (1.3.6.1.5.5.7.3.3)

---

## 📚 Related Files

| File | Purpose |
|------|---------|
| `install.ps1` | Interactive end-user installer |
| `install.bat` | Batch wrapper for install.ps1 |
| `installer.nsi` | NSIS packaged installer script |
| `build.ps1` | Build + sign AutoDJ.exe |
| `build_installer.bat` | Windows NSIS builder |
| `scripts/build_installer.ps1` | Cross-platform NSIS builder |
| `scripts/build_installer_linux.sh` | Linux/Wine NSIS builder |
| `version_info.txt` | Version metadata for exe |
| `config.example.toml` | Config template |
| `uninstall.ps1` | Generated uninstaller template |

---

## 🔗 External Resources

- **NSIS Documentation**: https://nsis.sourceforge.io/Docs/
- **PyInstaller**: https://pyinstaller.org/en/stable/
- **winget packages**: https://winget.run/
- **VB-Cable**: https://vb-audio.com/Cable/
- **mpv**: https://mpv.io/installation/
- **yt-dlp**: https://github.com/yt-dlp/yt-dlp

---

*Generated from repository analysis. Update this document when installer logic changes.*