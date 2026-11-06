# Windows Build Evidence Specification

## Evidence Bundle Structure

Every build produces a standardized evidence bundle at:

```
D:\temp\autodj-windows-build-<timestamp>\
├── evidence/
│   ├── source-provenance/
│   ├── environment/
│   ├── dependencies/
│   ├── tests/
│   ├── build/
│   ├── installer/
│   ├── SHA256SUMS
│   ├── SHA256SUMS.sha256
│   └── build-result.json
├── worktree/          # Isolated Git checkout (if -KeepWorktree)
└── dist/              # Build artifacts
```

## File Specifications

### 1. Source Provenance (`source-provenance/source-provenance.json`)

```json
{
  "Repository": "cvsz/autodj",
  "RemoteUrl": "git@github.com:cvsz/autodj.git",
  "Branch": "main",
  "ApprovedSha": "a4df182e7fcb9e0d81306af15db6c43813e1dbff",
  "ActualBuildSha": "a4df182e7fcb9e0d81306af15db6c43813e1dbff",
  "Version": "0.2.6",
  "ShaValidated": true,
  "ValidationTimestamp": "2026-11-03T12:00:00Z",
  "GitStatus": "clean",
  "GitLog": "a4df182 Merge pull request #99...\n154db8e fix: remediate F-01 F-02 F-03..."
}
```

**Required fields:**
- `Repository` — Must be `cvsz/autodj`
- `ApprovedSha` — Must match parameter
- `ActualBuildSha` — Must equal `ApprovedSha`
- `Version` — Must be `0.2.6`
- `ShaValidated` — Must be `true`
- `GitStatus` — Must be `clean`

### 2. Environment (`environment/environment.json`)

```json
{
  "WindowsProductName": "Windows 11 Enterprise",
  "WindowsVersion": "10.0.26300",
  "OsBuildNumber": 26300,
  "OsArchitecture": "x64",
  "PowerShellVersion": "7.6.9",
  "PythonVersion": "3.14.8",
  "PyInstallerVersion": "6.22.3",
  "NSISVersion": "3.10",
  "PrerequisitesChecked": true,
  "Timestamp": "2026-11-03T12:00:00Z"
}
```

### 3. Dependencies (`dependencies/pip-freeze.txt`, `dependencies/pip-list.json`)

Complete `pip freeze` output and structured `pip list --format=json` output.

### 4. Test Results (`tests/test-results.xml`, `tests/test-results.txt`)

JUnit XML and human-readable output from:
- Full pytest suite
- Targeted regression tests (F-01, F-02, F-03)

### 5. Build Artifacts (`build/`)

| File | Description |
|------|-------------|
| `pyinstaller-build.log` | Full PyInstaller output |
| `artifact-inventory.json` | EXE metadata + SHA-256 |
| `AutoDJ.exe.sha256` | EXE SHA-256 (single line) |
| `signing-result.json` | Code signing verification |

**artifact-inventory.json:**
```json
{
  "Name": "AutoDJ.exe",
  "Path": "worktree/dist/AutoDJ.exe",
  "SHA256": "6002ded62d9c8c4b65a97f2559ba9e396997bd48c4a3d2a191cc8e1ac44d8c86",
  "Size": 34976846,
  "Version": "0.2.6",
  "BuiltAt": "2026-11-03T12:30:00Z"
}
```

### 5. Installer Artifacts (`installer/`)

| File | Description |
|------|-------------|
| `nsis-build.log` | Full makensis output |
| `installer-inventory.json` | Installer metadata + SHA-256 |
| `installer.sha256` | Installer SHA-256 |

### 6. Build Result (`build-result.json`)

```json
{
  "BuildId": "autodj-windows-build-20261103-120000",
  "Timestamp": "2026-11-03T12:00:00Z",
  "ApprovedSha": "a4df182e7fcb9e0d81306af15db6c43813e1dbff",
  "ActualBuildSha": "a4df182e7fcb9e0d81306af15db6c43813e1dbff",
  "Version": "0.2.6",
  "SourceValidated": true,
  "PrerequisitesMet": true,
  "TestsRun": true,
  "TestsPassed": true,
  "PyInstallerBuilt": true,
  "InstallerBuilt": true,
  "SigningDone": true,
  "CriticalFailure": false,
  "ExitCode": 0,
  "Duration": "00:15:30.123",
  "EndTime": "2026-11-03T12:15:30Z",
  "BuildScriptVersion": "1.0.0",
  "OutputDirectory": "D:\\temp\\autodj-windows-build-20261103-120000",
  "WorktreeDirectory": "D:\\temp\\autodj-windows-build-20261103-120000\\worktree"
}
```

### 7. Manifests (`SHA256SUMS`, `SHA256SUMS.sha256`)

```
<sha256>  relative/path/file1.json
<sha256>  relative/path/file2.txt
...
```

Generated with:
```powershell
Get-ChildItem -File -Recurse | Where-Object { $_.Name -notin @("SHA256SUMS","SHA256SUMS.sha256") } |
Sort-Object FullName | ForEach-Object {
    $hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower()
    $rel = [IO.Path]::GetRelativePath($root, $_.FullName)
    "$hash  $rel"
} | Set-Content SHA256SUMS
(Get-FileHash SHA256SUMS -Algorithm SHA256).Hash | Set-Content SHA256SUMS.sha256
```

## Verification Checklist

| Check | Command | Expected |
|-------|---------|----------|
| Manifest verified | `Get-FileHash SHA256SUMS -Algorithm SHA256` | Matches `SHA256SUMS.sha256` |
| All files present | Parse `SHA256SUMS`, verify each file | All exist |
| All hashes match | Recompute each file hash | All match |
| Source SHA correct | `build-result.json` → `ActualBuildSha` | Equals `ApprovedSha` |
| Version correct | `artifact-inventory.json` → `Version` | `0.2.6` |
| Tests passed | `build-result.json` → `TestsPassed` | `true` |
| EXE hash matches | `Get-FileHash AutoDJ.exe` | Matches `artifact-inventory.json` |

## Evidence Integrity Rules

1. **No self-reference** — Manifest never includes itself
2. **Relative paths only** — No absolute paths in manifest
3. **No duplicates** — Each file appears exactly once
4. **Sorted entries** — Deterministic ordering
5. **UTF-8 encoding** — Manifest files are UTF-8
6. **No secrets** — No tokens, keys, or credentials in any evidence file

## Independent Verification

An independent auditor can verify the entire build by:

1. Clone repository at exact SHA
2. Run build script with same parameters
3. Compare all artifact hashes
4. Compare all manifest hashes
4. Verify `build-result.json` matches expectations

## Governance Notes

- Evidence bundles are **immutable** after generation
- Do not modify evidence after generation
- Preserve original bundle for independent review
- Do not include secrets, tokens, or credentials
- Build script version tracked in `build-result.json`