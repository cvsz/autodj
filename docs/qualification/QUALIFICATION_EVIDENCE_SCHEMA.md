# AutoDJ Qualification Evidence Schema

**Repository:** `cvsz/autodj`  
**Date:** 2026-11-02  

---

## 1. Evidence Directory Structure

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

## 2. Schema Definitions

### 2.1 environment.json

```json
{
  "RunId": "20261102-120000",
  "TimestampUtc": "2026-11-02T12:00:00Z",
  "OverallStatus": "PASS",
  "WindowsEdition": "Windows 11 Pro",
  "WindowsBuild": 22631,
  "PowerShellVersion": "7.4.0",
  "PythonVersion": "3.11.9",
  "PythonPath": "C:\\Python311\\python.exe",
  "NsisVersion": "3.10",
  "NsisPath": "C:\\Program Files (x86)\\NSIS\\makensis.exe",
  "GitVersion": "git version 2.47.1",
  "Results": [
    {
      "Check": "Windows edition",
      "Status": "PASS",
      "Detail": "Windows 11 Pro (Build 22631)",
      "Evidence": "Windows 11 Pro",
      "TimestampUtc": "2026-11-02T12:00:00Z"
    }
  ]
}
```

### 2.2 repository.json

```json
{
  "Repository": "cvsz/autodj",
  "HeadSha": "4444636b8dbcbaa62c67bc9385ad6332d62102ca",
  "OriginMainSha": "4444636b8dbcbaa62c67bc9385ad6332d62102ca",
  "HeadMatchesOrigin": true,
  "TimestampUtc": "2026-11-02T12:00:00Z",
  "WorkingTreeClean": true
}
```

### 2.3 test-results.json

```json
{
  "RunId": "20261102-120000",
  "TimestampUtc": "2026-11-02T12:00:00Z",
  "Source": "python-pytest",
  "Summary": {
    "Passed": 175,
    "Failed": 0,
    "Blocked": 0,
    "NotRun": 0
  },
  "Results": []
}
```

### 2.4 installer-results.json

```json
{
  "RunId": "20261102-120000",
  "TimestampUtc": "2026-11-02T12:00:00Z",
  "Source": "powershell-installer-harness",
  "Summary": {
    "Passed": 13,
    "Failed": 0,
    "Blocked": 0,
    "NotRun": 0
  },
  "Results": [
    {
      "TestId": "INSTALL-01",
      "Status": "PASS",
      "Detail": "Fresh installation succeeded",
      "Evidence": "",
      "TimestampUtc": "2026-11-02T12:00:00Z"
    }
  ]
}
```

### 2.5 runtime-results.json

```json
{
  "RunId": "20261102-120000",
  "TimestampUtc": "2026-11-02T12:00:00Z",
  "Source": "powershell-runtime-harness",
  "Summary": {
    "Passed": 8,
    "Failed": 0,
    "Blocked": 0,
    "NotRun": 4
  },
  "Results": [
    {
      "TestId": "RUNTIME-01",
      "Status": "PASS",
      "Detail": "AutoDJ.exe --version exited 0",
      "Evidence": "",
      "Simulated": false,
      "TimestampUtc": "2026-11-02T12:00:00Z"
    }
  ]
}
```

### 2.6 checksums.sha256

```
a1b2c3d4e5f6...  environment.json
f7e8d9c0b1a2...  repository.json
...
```

---

## 3. Status Values

| Value | Meaning |
|-------|---------|
| PASS | Test passed |
| FAIL | Test failed |
| BLOCKED | External dependency missing |
| NOT RUN | Test not applicable |

---

## 4. Sanitization Rules

All log files included in `sanitized-logs/` must have the following redacted:

- Passwords and secret values
- Access tokens and API keys
- Private keys and certificate material
- Camfrog credentials and nicknames (except operator's own)
- Personal information

Redaction pattern: `KEY=***REDACTED***`

---

## 5. Evidence Collection Command

```powershell
.\tools\windows-qualification\Collect-AutoDJEvidence.ps1 `
    -OutputDir ./artifacts/qualification `
    -EnvironmentJson ./doctor.json `
    -TestResults ./test-results.json `
    -InstallerResults ./installer-results.json `
    -RuntimeResults ./runtime-results.json `
    -LogFiles ./build.log,./install.log
```
