# AutoDJ Windows 11 Reproducible Build Guide

## Overview

This document describes the reproducible build process for AutoDJ v0.2.6 on Windows 11.

## Prerequisites

- **Windows 11** (Build 22000+) x64
- **PowerShell 5.1+** or **PowerShell 7+**
- **Python 3.11+** (64-bit)
- **Git** (with SSH access to `git@github.com:cvsz/autodj.git`)
- **PyInstaller 6.22+** (installed via pip)
- **NSIS 3.10+** (optional, for installer build)
- **Code signing certificate** (optional, for signed builds)

## Quick Start

```powershell
# Build with default settings (requires code signing certificate or self-sign)
.\scripts\build_windows.ps1 -ApprovedSha "a4df182e7fcb9e0d81306af15db6c43813e1dbff"

# Build without signing (development)
.\scripts\build_windows.ps1 -ApprovedSha "a4df182e7fcb9e0d81306af15db6c43813e1dbff" -NoSign

# Build without tests (faster iteration)
.\scripts\build_windows.ps1 -ApprovedSha "a4df182e7fcb9e0d81306af15db6c43813e1dbff" -NoSign -SkipTests

# Build with custom output directory
.\scripts\build_windows.ps1 -ApprovedSha "a4df182e7fcb9e0d81306af15db6c43813e1dbff" -OutputRoot "E:\builds"
```

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `ApprovedSha` | **Yes** | — | Exact 40-char commit SHA to build |
| `OutputRoot` | No | `D:\temp\autodj-windows-build` | Root directory for evidence bundle |
| `SkipTests` | No | `$false` | Skip Windows test suite |
| `SkipInstaller` | No | `$false` | Skip NSIS installer build |
| `KeepWorktree` | No | `$false` | Preserve isolated worktree after build |
| `NoSign` | No | `$false` | Skip code signing |
| `Pfx` | No | `$env:AUTODJ_PFX` | Path to PFX certificate |
| `Password` | No | `$env:AUTODJ_PFX_PASSWORD` | PFX password |
| `Thumbprint` | No | `$env:AUTODJ_CERT_THUMBPRINT` | Certificate thumbprint in Windows store |
| `Subject` | No | `CN=ZEAZDEV...` | Self-signed cert subject |
| `Name` | No | `AutoDJ` | Output executable name |
| `Detailed` | No | `$false` | Verbose output |

## Build Process

The script performs these steps:

1. **Source Validation**
   - Creates isolated Git worktree at exact `ApprovedSha`
   - Verifies repository identity, branch, and working tree cleanliness
   - Validates version metadata matches `0.2.6`

2. **Prerequisite Checks**
   - Windows 11 (Build 22000+), x64
   - Python 3.11+, PyInstaller 6.22+
   - NSIS 3.10+ (if installer not skipped)
   - Sufficient disk space (≥5 GB)

3. **Dependency Installation**
   - Runs `tools/check_build_env.py` pre-flight
   - Installs project in editable mode with `pyinstaller` extra

4. **Test Execution** (unless `-SkipTests`)
   - Full pytest suite with JUnit XML output
   - Targeted regression tests for F-01, F-02, F-03 remediation

5. **PyInstaller Build**
   - Clean build using `--clean`, `--noupx`, `--windowed`
   - Bundles: `camfrog_autodj`, `pywinauto`, `pyttsx3`, `yt_dlp`, `comtypes`, `pyperclip`, `mutagen`
   - Copies `config.example.toml` → `dist/config.toml`
   - Bundles `mpv/` directory
   - Smoke test: `AutoDJ.exe --version`

6. **Code Signing** (unless `-NoSign`)
   - PFX file (`-Pfx` / `AUTODJ_PFX`)
   - Windows store thumbprint (`-Thumbprint` / `AUTODJ_CERT_THUMBPRINT`)
   - Self-signed cert (default, trusted on build machine)

7. **NSIS Installer Build** (unless `-SkipInstaller`)
   - Runs `makensis /DAPP_VERSION=0.2.6 installer.nsi`
   - Output: `Camfrog-AutoDJ-Setup-0.2.6.exe`

8. **Evidence Bundle Generation**
   - SHA-256 manifests for all artifacts
   - Machine-readable JSON results
   - Complete provenance trail

## Output Structure

```
D:\temp\autodj-windows-build-<timestamp>\
├── evidence/
│   ├── source-provenance/
│   │   └── source-provenance.json
│   ├── environment/
│   │   └── environment.json
│   ├── dependencies/
│   │   ├── pip-freeze.txt
│   │   └── pip-list.json
│   ├── tests/
│   │   ├── test-results.xml
│   │   ├── test-results.txt
│   │   └── regression-test-results.xml
│   ├── build/
│   │   ├── pyinstaller-build.log
│   │   ├── artifact-inventory.json
│   │   ├── AutoDJ.exe.sha256
│   │   └── signing-result.json
│   ├── installer/
│   │   ├── nsis-build.log
│   │   ├── installer-inventory.json
│   │   └── installer.sha256
│   ├── build-result.json
│   ├── SHA256SUMS
│   └── SHA256SUMS.sha256
├── worktree/          # (if -KeepWorktree)
└── dist/
    ├── AutoDJ.exe
    ├── config.toml
    └── mpv/
```

## Artifacts

| Artifact | Description | Location |
|----------|-------------|----------|
| `AutoDJ.exe` | Signed/Unsigned executable | `worktree/dist/AutoDJ.exe` |
| `Camfrog-AutoDJ-Setup-0.2.6.exe` | NSIS installer | Worktree root |
| `build-result.json` | Machine-readable build result | `evidence/build-result.json` |
| `SHA256SUMS` | Manifest of all evidence files | `evidence/SHA256SUMS` |
| `SHA256SUMS.sha256` | Manifest self-hash | `evidence/SHA256SUMS.sha256` |

## Verification

```powershell
# Verify manifest integrity
cd evidence
$lines = Get-Content SHA256SUMS
foreach ($line in $lines) {
    $hash, $file = $line -split "\s+", 2
    $actual = (Get-FileHash $file -Algorithm SHA256).Hash.ToLower()
    if ($hash -ne $actual) { throw "MISMATCH: $file" }
}
Write-Host "All hashes verified" -ForegroundColor Green
```

## CI/CD Integration

The script is designed for use in Windows CI runners:

```yaml
# GitHub Actions example
- name: Windows Build
  uses: actions/checkout@v4
  with:
    ref: ${{ github.event.inputs.sha }}  # Must specify exact SHA

- name: Build
  run: |
    .\scripts\build_windows.ps1 `
      -ApprovedSha "${{ github.event.inputs.sha }}" `
      -OutputRoot "${{ runner.temp }}\autodj-build" `
      -NoSign `
      -SkipInstaller
```

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| "python not found" | Install Python 3.11+ and ensure on PATH |
| "makensis not found" | Install NSIS 3.10+ or use `-SkipInstaller` |
| "Certificate not found" | Provide `-Pfx`, `-Thumbprint`, or allow self-sign |
| "Worktree already exists" | Use `-KeepWorktree` to preserve, or delete manually |
| "SHA mismatch" | Ensure `ApprovedSha` matches exact 40-char commit |

## Security Notes

- Never commit certificates or passwords to repository
- Use environment variables (`AUTODJ_PFX`, `AUTODJ_PFX_PASSWORD`, `AUTODJ_CERT_THUMBPRINT`) for secrets
- Self-signed certificates are only trusted on the build machine
- For production distribution, use a real code-signing certificate (OV/EV)
- Never disable TLS verification in application code

## Governance

This build script **does not**:
- Create Git tags
- Publish GitHub Releases
- Deploy artifacts
- Merge PRs
- Grant release authorization

Release authorization requires:
1. Independent review by `policedbc`
2. Complete Windows qualification evidence
3. Explicit operator authorization