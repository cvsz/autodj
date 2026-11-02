# AutoDJ Windows Qualification Guide

**Repository:** `cvsz/autodj`  
**Base Commit:** `4444636` (Merge PR #85)  
**Date:** 2026-11-02  

---

## 1. Overview

The Windows Qualification Kit provides reproducible, evidence-based testing
for AutoDJ on Windows 11. It consists of PowerShell scripts in
`tools/windows-qualification/` and `tools/camfrog-qualification/` that:

1. **Doctor** - Diagnose the host environment (`Invoke-AutoDJDoctor.ps1`)
2. **Build** - Build AutoDJ.exe and the NSIS installer (`Build-AutoDJ.ps1`)
3. **Installer tests** - Test install/upgrade/uninstall lifecycle
   (`Test-AutoDJInstaller.ps1`)
4. **Runtime tests** - Test AutoDJ startup, config, process lifecycle
   (`Test-AutoDJRuntime.ps1`)
5. **Code signing** - Validate certificate readiness
   (`Test-AutoDJCodeSigning.ps1`)
6. **Evidence collection** - Gather machine-readable evidence
   (`Collect-AutoDJEvidence.ps1`)
7. **Camfrog tests** - Unit and mock integration tests
   (`tools/camfrog-qualification/`)

---

## 2. Prerequisites

| Component | Minimum Version | Notes |
|-----------|----------------|-------|
| Windows | 11 (Build 22000+) | Required for NSIS installer |
| PowerShell | 5.1+ | 7 recommended |
| Python | 3.11+ | Required for build and tests |
| NSIS | 3.08+ | Required for installer compilation |
| Git | Any recent | Required for version verification |
| GitHub CLI | Optional | Required for CI integration |

---

## 3. Running the Qualification Kit

### 3.1 Environment Doctor

```powershell
# Read-only diagnostic (no system changes)
.\tools\windows-qualification\Invoke-AutoDJDoctor.ps1

# Write JSON output
.\tools\windows-qualification\Invoke-AutoDJDoctor.ps1 -OutputPath ./doctor.json
```

### 3.2 Build Runner

```powershell
# Unsigned development build
.\tools\windows-qualification\Build-AutoDJ.ps1 -OutputDir ./build-output

# Signed release build (requires certificate secrets)
.\tools\windows-qualification\Build-AutoDJ.ps1 -OutputDir ./build-output -Pfx cert\autodj.pfx -Password "***REDACTED***"
```

### 3.3 Installer Lifecycle Tests

```powershell
.\tools\windows-qualification\Test-AutoDJInstaller.ps1 -InstallerPath ./dist/Camfrog-AutoDJ-Setup-0.2.6.exe
```

### 3.4 Runtime Tests

```powershell
.\tools\windows-qualification\Test-AutoDJRuntime.ps1 -ExePath ./dist/AutoDJ.exe
```

### 3.5 Code Signing Readiness

```powershell
.\tools\windows-qualification\Test-AutoDJCodeSigning.ps1
```

### 3.6 Evidence Collection

```powershell
.\tools\windows-qualification\Collect-AutoDJEvidence.ps1 -OutputDir ./artifacts/qualification
```

### 3.7 Camfrog Integration Tests

```powershell
# Unit + mock tests only (no live Camfrog)
.\tools\camfrog-qualification\Test-AutoDJCamfrogIntegration.ps1

# Live tests (requires credentials, isolated test room only)
.\tools\camfrog-qualification\Test-AutoDJCamfrogIntegration.ps1 `
    -RunLive `
    -CamfrogNick "TestBot" `
    -CamfrogRoom "QualificationTest"
```

---

## 4. Evidence Directory Structure

```
artifacts/qualification/<run-id>/
├── environment.json          # Host environment details
├── repository.json           # Git HEAD and origin/main SHAs
├── test-results.json         # Python test results
├── installer-results.json    # Installer lifecycle results
├── runtime-results.json      # Runtime test results
├── checksums.sha256          # SHA256 of all artifacts
├── sanitized-logs/           # Sanitized log files
│   └── ...
└── summary.md                # Human-readable summary
```

---

## 5. Safe Execution Rules

| Rule | Rationale |
|------|-----------|
| Never test against real user directories | Use disposable temp directories only |
| Never expose secrets in logs | All scripts sanitize secrets automatically |
| Never use self-signed cert as production proof | Self-signed certs are for development only |
| Never run destructive ops outside test dirs | All installer tests use temp dirs |
| Never auto-run live Camfrog tests | Requires explicit `-RunLive` flag |

---

## 6. Failure Interpretation

| Status | Meaning | Action |
|--------|---------|--------|
| PASS | Test passed | No action needed |
| FAIL | Test failed | Investigate and remediate |
| BLOCKED | External dependency missing | Document blocker, do not proceed |
| NOT RUN | Test not applicable | Document reason |

---

## 7. Cleanup

All test harnesses clean up their temporary directories by default. Use
`-NoCleanup` to preserve them for debugging.

Rollback: No system configuration is modified by any script. Uninstalling
AutoDJ removes only application-owned files; user data (config.toml,
playlist.json, logs) is preserved.
