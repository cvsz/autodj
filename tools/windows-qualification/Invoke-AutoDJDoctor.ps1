<#
.SYNOPSIS
    AutoDJ Environment Doctor - Read-only diagnostic for Windows qualification.

.DESCRIPTION
    Performs a read-only audit of the host environment to determine readiness
    for building, installing, and running AutoDJ on Windows. Never modifies
    system configuration, never writes secrets, and never performs destructive
    operations.

    Exit codes:
        0 = All checks passed (or non-critical warnings only)
        1 = One or more critical failures
        2 = Script error / unexpected exception

.OUTPUTS
    Machine-readable JSON to stdout containing environment details and check results.

.PARAMETER OutputPath
    Optional path to write the JSON result file. If omitted, JSON is written to stdout only.

.PARAMETER Format
    Output format: "json" (default) or "summary".

.EXAMPLE
    .\Invoke-AutoDJDoctor.ps1
    .\Invoke-AutoDJDoctor.ps1 -OutputPath C:\Temp\autodj-doctor.json
    .\Invoke-AutoDJDoctor.ps1 -Format summary
#>
[CmdletBinding()]
param(
    [string]$OutputPath,
    [ValidateSet("json", "summary")]
    [string]$Format = "json"
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-Result {
    param(
        [string]$Check,
        [string]$Status,   # PASS, FAIL, WARN, BLOCKED, NOT RUN
        [string]$Detail,
        [string]$Evidence = ""
    )
    $script:Results += [pscustomobject]@{
        Check        = $Check
        Status       = $Status
        Detail       = $Detail
        Evidence     = $Evidence
        TimestampUtc = (Get-Date -Format "o")
    }
}

function Test-Command {
    param([string]$Name)
    return (Get-Command $Name -ErrorAction SilentlyContinue) -ne $null
}

function Test-FileOrDir {
    param([string]$Path)
    return Test-Path $Path -ErrorAction SilentlyContinue
}

function Get-RegistryValue {
    param([string]$Key, [string]$Value)
    try {
        $item = Get-ItemProperty -Path $Key -Name $Value -ErrorAction Stop
        return $item.$Value
    } catch {
        return $null
    }
}

# ---------------------------------------------------------------------------
# Initialize
# ---------------------------------------------------------------------------

$script:Results = @()
$script:HasCriticalFailure = $false
$runId = (Get-Date -Format "yyyyMMdd-HHmmss")

Write-Host "=== AutoDJ Environment Doctor ===" -ForegroundColor Cyan
Write-Host "Run ID: $runId"
Write-Host "Timestamp: $(Get-Date -Format 'o')"
Write-Host ""

# ---------------------------------------------------------------------------
# 1. Windows edition and build
# ---------------------------------------------------------------------------

try {
    $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
    $osName = $os.Caption
    $osBuild = $os.BuildNumber
    $osArch = $os.OSArchitecture
    Write-Result -Check "Windows edition" -Status "PASS" -Detail "$osName (Build $osBuild)" -Evidence $osName
    Write-Result -Check "Windows architecture" -Status "PASS" -Detail $osArch -Evidence $osArch

    $isWin11 = $osBuild -ge 22000
    if ($isWin11) {
        Write-Result -Check "Windows 11+ (Build 22000+)" -Status "PASS" -Detail "Build $osBuild meets minimum requirement"
    } else {
        Write-Result -Check "Windows 11+ (Build 22000+)" -Status "FAIL" -Detail "Build $osBuild is below minimum 22000"
        $script:HasCriticalFailure = $true
    }
} catch {
    Write-Result -Check "Windows edition" -Status "FAIL" -Detail "Unable to query OS: $_"
    $script:HasCriticalFailure = $true
}

# ---------------------------------------------------------------------------
# 2. PowerShell version
# ---------------------------------------------------------------------------

$psVersion = $PSVersionTable.PSVersion
$psVersionStr = "$($psVersion.Major).$($psVersion.Minor).$($psVersion.Build)"
Write-Result -Check "PowerShell version" -Status "PASS" -Detail $psVersionStr -Evidence $psVersionStr

if ($psVersion.Major -ge 5) {
    Write-Result -Check "PowerShell 5.1+" -Status "PASS" -Detail "Version $psVersionStr"
} else {
    Write-Result -Check "PowerShell 5.1+" -Status "FAIL" -Detail "Version $psVersionStr is below 5.1"
    $script:HasCriticalFailure = $true
}

# ---------------------------------------------------------------------------
# 3. Python
# ---------------------------------------------------------------------------

$pythonFound = $false
$pythonVersion = $null
$pythonPath = $null

foreach ($cmd in @("python", "python3", "py")) {
    $cmdObj = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($cmdObj) {
        try {
            $verOut = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null
            if ($verOut) {
                $pythonFound = $true
                $pythonVersion = $verOut.Trim()
                $pythonPath = $cmdObj.Source
                break
            }
        } catch { }
    }
}

if ($pythonFound) {
    Write-Result -Check "Python" -Status "PASS" -Detail "$pythonVersion at $pythonPath" -Evidence $pythonPath

    $majorMinor = [version]$pythonVersion
    if ($majorMinor -ge [version]"3.11") {
        Write-Result -Check "Python 3.11+" -Status "PASS" -Detail "Version $pythonVersion"
    } else {
        Write-Result -Check "Python 3.11+" -Status "FAIL" -Detail "Version $pythonVersion is below 3.11"
        $script:HasCriticalFailure = $true
    }
} else {
    Write-Result -Check "Python" -Status "FAIL" -Detail "Python not found on PATH"
    $script:HasCriticalFailure = $true
}

# ---------------------------------------------------------------------------
# 4. NSIS
# ---------------------------------------------------------------------------

$nsisFound = $false
$nsisVersion = $null
$nsisPath = $null

$nsisCmd = Get-Command "makensis" -ErrorAction SilentlyContinue
if ($nsisCmd) {
    try {
        $verOut = & $nsisCmd /VERSION 2>$null
        if ($verOut) {
            $nsisFound = $true
            $nsisVersion = $verOut.Trim()
            $nsisPath = $nsisCmd.Source
        }
    } catch { }
}

if (-not $nsisFound) {
    # Check common install locations
    $commonPaths = @(
        "C:\Program Files (x86)\NSIS\makensis.exe",
        "C:\Program Files\NSIS\makensis.exe"
    )
    foreach ($p in $commonPaths) {
        if (Test-Path $p) {
            try {
                $verOut = & $p /VERSION 2>$null
                if ($verOut) {
                    $nsisFound = $true
                    $nsisVersion = $verOut.Trim()
                    $nsisPath = $p
                    break
                }
            } catch { }
        }
    }
}

if ($nsisFound) {
    Write-Result -Check "NSIS (makensis)" -Status "PASS" -Detail "$nsisVersion at $nsisPath" -Evidence $nsisPath
} else {
    Write-Result -Check "NSIS (makensis)" -Status "FAIL" -Detail "NSIS not found on PATH or common locations"
    $script:HasCriticalFailure = $true
}

# ---------------------------------------------------------------------------
# 5. Git and GitHub CLI
# ---------------------------------------------------------------------------

$gitCmd = Get-Command "git" -ErrorAction SilentlyContinue
if ($gitCmd) {
    try {
        $gitVer = & $gitCmd --version 2>$null
        Write-Result -Check "Git" -Status "PASS" -Detail $gitVer.Trim() -Evidence $gitCmd.Source
    } catch {
        Write-Result -Check "Git" -Status "WARN" -Detail "Git found but version query failed"
    }
} else {
    Write-Result -Check "Git" -Status "FAIL" -Detail "Git not found on PATH"
    $script:HasCriticalFailure = $true
}

$ghCmd = Get-Command "gh" -ErrorAction SilentlyContinue
if ($ghCmd) {
    try {
        $ghVer = & $gh --version 2>$null
        Write-Result -Check "GitHub CLI (gh)" -Status "PASS" -Detail $ghVer.Trim() -Evidence $ghCmd.Source
    } catch {
        Write-Result -Check "GitHub CLI (gh)" -Status "WARN" -Detail "gh found but version query failed"
    }
} else {
    Write-Result -Check "GitHub CLI (gh)" -Status "WARN" -Detail "gh not found on PATH (optional for local qualification)"
}

# ---------------------------------------------------------------------------
# 6. Audio devices
# ---------------------------------------------------------------------------

try {
    $audioDevices = Get-CimInstance Win32_SoundDevice -ErrorAction SilentlyContinue
    if ($audioDevices) {
        $devCount = ($audioDevices | Measure-Object).Count
        $devNames = ($audioDevices | ForEach-Object { $_.Name }) -join ", "
        Write-Result -Check "Audio devices" -Status "PASS" -Detail "$devCount device(s): $devNames" -Evidence $devNames
    } else {
        Write-Result -Check "Audio devices" -Status "WARN" -Detail "No audio devices detected (audio playback may not work)"
    }
} catch {
    Write-Result -Check "Audio devices" -Status "WARN" -Detail "Unable to query audio devices: $_"
}

# ---------------------------------------------------------------------------
# 7. Disk space
# ---------------------------------------------------------------------------

try {
    $sysDrive = [System.IO.Path]::GetPathRoot((Get-Location).Path)
    $drive = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$sysDrive'" -ErrorAction SilentlyContinue
    if ($drive) {
        $freeGB = [math]::Round($drive.FreeSpace / 1GB, 2)
        $sizeGB = [math]::Round($drive.Size / 1GB, 2)
        Write-Result -Check "Disk space ($sysDrive)" -Status "PASS" -Detail "$freeGB GB free of $sizeGB GB" -Evidence "$freeGB GB free"
        if ($freeGB -lt 5) {
            Write-Result -Check "Disk space >= 5 GB" -Status "WARN" -Detail "Only $freeGB GB free on $sysDrive"
        } else {
            Write-Result -Check "Disk space >= 5 GB" -Status "PASS" -Detail "$freeGB GB free on $sysDrive"
        }
    } else {
        Write-Result -Check "Disk space" -Status "WARN" -Detail "Unable to query system drive"
    }
} catch {
    Write-Result -Check "Disk space" -Status "WARN" -Detail "Unable to query disk space: $_"
}

# ---------------------------------------------------------------------------
# 8. Write permissions
# ---------------------------------------------------------------------------

try {
    $testDir = Join-Path $env:TEMP "autodj-doctor-test-$runId"
    New-Item -ItemType Directory -Path $testDir -ErrorAction Stop | Out-Null
    $testFile = Join-Path $testDir "write-test.tmp"
    "test" | Set-Content -Path $testFile -ErrorAction Stop
    $readBack = Get-Content -Path $testFile -ErrorAction Stop
    Remove-Item -Path $testDir -Recurse -Force -ErrorAction SilentlyContinue
    Write-Result -Check "TEMP write permission" -Status "PASS" -Detail "Able to create, write, and read files in $env:TEMP"
} catch {
    Write-Result -Check "TEMP write permission" -Status "FAIL" -Detail "Unable to write to $env:TEMP: $_"
    $script:HasCriticalFailure = $true
}

# ---------------------------------------------------------------------------
# 9. Python dependencies (if Python found)
# ---------------------------------------------------------------------------

if ($pythonFound) {
    $requiredModules = @("yt_dlp", "mutagen", "pyttsx3", "pywinauto", "pyperclip")
    foreach ($mod in $requiredModules) {
        try {
            & $pythonPath -c "import $mod" 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Result -Check "Python module: $mod" -Status "PASS" -Detail "Module $mod is importable"
            } else {
                Write-Result -Check "Python module: $mod" -Status "WARN" -Detail "Module $mod not importable"
            }
        } catch {
            Write-Result -Check "Python module: $mod" -Status "WARN" -Detail "Module $mod check failed"
        }
    }
}

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

$summary = [pscustomobject]@{
    RunId              = $runId
    TimestampUtc       = (Get-Date -Format "o")
    OverallStatus      = if ($script:HasCriticalFailure) { "FAIL" } else { "PASS" }
    WindowsEdition     = if ($os) { $osName } else { $null }
    WindowsBuild       = if ($os) { $osBuild } else { $null }
    PowerShellVersion  = $psVersionStr
    PythonVersion      = $pythonVersion
    PythonPath         = $pythonPath
    NsisVersion        = $nsisVersion
    NsisPath           = $nsisPath
    GitVersion         = if ($gitCmd) { ( & $gitCmd --version 2>$null ).Trim() } else { $null }
    Results            = $script:Results
}

if ($Format -eq "summary") {
    Write-Host ""
    Write-Host "=== Summary ===" -ForegroundColor Cyan
    foreach ($r in $script:Results) {
        $color = switch ($r.Status) {
            "PASS"   { "Green" }
            "FAIL"   { "Red" }
            "WARN"   { "Yellow" }
            "BLOCKED" { "Red" }
            default { "White" }
        }
        Write-Host ("[{0}] {1} - {2}" -f $r.Status, $r.Check, $r.Detail) -ForegroundColor $color
    }
    Write-Host ""
    Write-Host ("Overall: {0}" -f $summary.OverallStatus) -ForegroundColor Cyan
}

$json = $summary | ConvertTo-Json -Depth 10

if ($OutputPath) {
    $json | Set-Content -Path $OutputPath -Encoding UTF8
    Write-Host ""
    Write-Host ("JSON output written to: $OutputPath") -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host $json
}

if ($script:HasCriticalFailure) {
    exit 1
} else {
    exit 0
}