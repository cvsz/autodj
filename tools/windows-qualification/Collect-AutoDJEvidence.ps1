<#
.SYNOPSIS
    AutoDJ Evidence Collector.

.DESCRIPTION
    Collects qualification evidence into a machine-readable directory structure:

        artifacts/qualification/<run-id>/
            environment.json
            repository.json
            test-results.json
            installer-results.json
            runtime-results.json
            checksums.sha256
            sanitized-logs/
            summary.md

    Never includes secrets, access tokens, passwords, private keys, or
    Camfrog credentials.

.PARAMETER OutputDir
    Root output directory. Default: ./artifacts/qualification

.PARAMETER EnvironmentJson
    Path to environment.json from Invoke-AutoDJDoctor.ps1

.PARAMETER TestResults
    Path to test-results.json (from any test harness)

.PARAMETER InstallerResults
    Path to installer-results.json

.PARAMETER RuntimeResults
    Path to runtime-results.json

.PARAMETER LogFiles
    Comma-separated list of log files to sanitize and include

.EXAMPLE
    .\Collect-AutoDJEvidence.ps1 -OutputDir ./artifacts/qualification
    .\Collect-AutoDJEvidence.ps1 -EnvironmentJson ./doctor.json -TestResults ./test-results.json
#>
[CmdletBinding()]
param(
    [string]$OutputDir = "artifacts/qualification",
    [string]$EnvironmentJson = "",
    [string]$TestResults = "",
    [string]$InstallerResults = "",
    [string]$RuntimeResults = "",
    [string]$LogFiles = ""
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Initialize
# ---------------------------------------------------------------------------

$runId = (Get-Date -Format "yyyyMMdd-HHmmss")
$outputRoot = Resolve-Path $OutputDir -ErrorAction SilentlyContinue
if (-not $outputRoot) {
    $outputRoot = Join-Path (Get-Location) $OutputDir
    New-Item -ItemType Directory -Path $outputRoot -ErrorAction Stop | Out-Null
}
$runDir = Join-Path $outputRoot $runId
$logsDir = Join-Path $runDir "sanitized-logs"
New-Item -ItemType Directory -Path $runDir -ErrorAction Stop | Out-Null
New-Item -ItemType Directory -Path $logsDir -ErrorAction Stop | Out-Null

Write-Host "=== AutoDJ Evidence Collector ===" -ForegroundColor Cyan
Write-Host "Run ID: $runId"
Write-Host "Output dir: $runDir"
Write-Host ""

# ---------------------------------------------------------------------------
# Helper: sanitize file content
# ---------------------------------------------------------------------------

function Sanitize-Content {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $null }
    try {
        $content = Get-Content -Path $Path -Raw -ErrorAction Stop
        # Remove potential secrets
        $content = $content -replace '(?i)(password|secret|token|key|pfx|credential)\s*[:=]\s*["\x27][^"\x27]+["\x27]', '$1=***REDACTED***'
        $content = $content -replace '(?i)(AUTODJ_PFX|AUTODJ_PFX_PASSWORD|AUTODJ_CERT_THUMBPRINT)\s*[:=]\s*\S+', '$1=***REDACTED***'
        return $content
    } catch {
        return "[Unable to read: $_]"
    }
}

# ---------------------------------------------------------------------------
# Collect environment.json
# ---------------------------------------------------------------------------

if ($EnvironmentJson -and (Test-Path $EnvironmentJson)) {
    Copy-Item -Path $EnvironmentJson -Destination (Join-Path $runDir "environment.json") -ErrorAction Stop
    Write-Host "Collected: environment.json" -ForegroundColor Green
} else {
    $envSummary = [pscustomobject]@{
        RunId              = $runId
        TimestampUtc       = (Get-Date -Format "o")
        CollectedFrom      = "live-system"
        WindowsEdition     = (Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue).Caption
        WindowsBuild       = (Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue).BuildNumber
        PowerShellVersion  = $PSVersionTable.PSVersion.ToString()
        PythonVersion      = $null
        Notes              = "Collected live; no doctor output provided"
    }
    $envSummary | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path $runDir "environment.json") -Encoding UTF8
    Write-Host "Collected: environment.json (live)" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# Collect repository.json
# ---------------------------------------------------------------------------

$scriptRoot = (Get-Item (Resolve-Path $PSScriptRoot).Parent.Parent).FullName
$headSha = & git rev-parse HEAD 2>$null
$originSha = & git rev-parse origin/main 2>$null
$repoJson = [pscustomobject]@{
    Repository         = "cvsz/autodj"
    HeadSha            = $headSha
    OriginMainSha      = $originSha
    HeadMatchesOrigin  = ($headSha -eq $originSha)
    TimestampUtc       = (Get-Date -Format "o")
    WorkingTreeClean   = -not ((git status --short 2>$null))
}
$repoJson | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path $runDir "repository.json") -Encoding UTF8
Write-Host "Collected: repository.json" -ForegroundColor Green

# ---------------------------------------------------------------------------
# Collect test results
# ---------------------------------------------------------------------------

if ($TestResults -and (Test-Path $TestResults)) {
    Copy-Item -Path $TestResults -Destination (Join-Path $runDir "test-results.json") -ErrorAction Stop
    Write-Host "Collected: test-results.json" -ForegroundColor Green
} else {
    [pscustomobject]@{
        RunId         = $runId
        TimestampUtc  = (Get-Date -Format "o")
        Source        = "not-provided"
        Summary       = @{ Passed = 0; Failed = 0; Blocked = 0; NotRun = 0 }
        Results       = @()
    } | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path $runDir "test-results.json") -Encoding UTF8
    Write-Host "Collected: test-results.json (empty)" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Collect installer results
# ---------------------------------------------------------------------------

if ($InstallerResults -and (Test-Path $InstallerResults)) {
    Copy-Item -Path $InstallerResults -Destination (Join-Path $runDir "installer-results.json") -ErrorAction Stop
    Write-Host "Collected: installer-results.json" -ForegroundColor Green
} else {
    [pscustomobject]@{
        RunId         = $runId
        TimestampUtc  = (Get-Date -Format "o")
        Source        = "not-provided"
        Summary       = @{ Passed = 0; Failed = 0; Blocked = 0; NotRun = 0 }
        Results       = @()
    } | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path $runDir "installer-results.json") -Encoding UTF8
    Write-Host "Collected: installer-results.json (empty)" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Collect runtime results
# ---------------------------------------------------------------------------

if ($RuntimeResults -and (Test-Path $RuntimeResults)) {
    Copy-Item -Path $RuntimeResults -Destination (Join-Path $runDir "runtime-results.json") -ErrorAction Stop
    Write-Host "Collected: runtime-results.json" -ForegroundColor Green
} else {
    [pscustomobject]@{
        RunId         = $runId
        TimestampUtc  = (Get-Date -Format "o")
        Source        = "not-provided"
        Summary       = @{ Passed = 0; Failed = 0; Blocked = 0; NotRun = 0 }
        Results       = @()
    } | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path $runDir "runtime-results.json") -Encoding UTF8
    Write-Host "Collected: runtime-results.json (empty)" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Collect log files (sanitized)
# ---------------------------------------------------------------------------

if ($LogFiles) {
    $logPaths = $LogFiles -split ","
    foreach ($logPath in $logPaths) {
        $logPath = $logPath.Trim()
        if (Test-Path $logPath) {
            $content = Sanitize-Content -Path $logPath
            $fileName = [System.IO.Path]::GetFileName($logPath)
            $destPath = Join-Path $logsDir $fileName
            $content | Set-Content -Path $destPath -Encoding UTF8
            Write-Host "Collected log: $fileName" -ForegroundColor Green
        }
    }
}

# ---------------------------------------------------------------------------
# Generate checksums
# ---------------------------------------------------------------------------

$checksumFile = Join-Path $runDir "checksums.sha256"
$files = Get-ChildItem -Path $runDir -File | Where-Object { $_.Name -ne "checksums.sha256" }
$checksums = @()
foreach ($f in $files) {
    $hash = Get-FileHash -Path $f.FullName -Algorithm SHA256
    $checksums += "$($hash.Hash.ToLower())  $($f.Name)"
}
$checksums | Set-Content -Path $checksumFile -Encoding UTF8
Write-Host "Generated: checksums.sha256" -ForegroundColor Green

# ---------------------------------------------------------------------------
# Generate summary.md
# ---------------------------------------------------------------------------

$envContent = Get-Content -Path (Join-Path $runDir "environment.json") -Raw -ErrorAction SilentlyContinue
$repoContent = Get-Content -Path (Join-Path $runDir "repository.json") -Raw -ErrorAction SilentlyContinue

$summary = @"
# AutoDJ Qualification Evidence Summary

**Run ID:** $runId
**Timestamp:** $(Get-Date -Format 'o')
**Repository:** cvsz/autodj
**Head SHA:** $headSha
**Origin/main SHA:** $originSha
**Head matches origin:** $($repoJson.HeadMatchesOrigin)

## Files Collected

$(Get-ChildItem -Path $runDir -File | ForEach-Object { "- $($_.Name)" })

## Environment

$(if ($envContent) { $envContent } else { "Not collected" })

## Results

Test results, installer results, and runtime results are available as JSON
files in this directory. See QUALIFICATION_EVIDENCE_SCHEMA.md for the schema.

## Checksums

$(Get-Content -Path $checksumFile)

"@
$summary | Set-Content -Path (Join-Path $runDir "summary.md") -Encoding UTF8
Write-Host "Generated: summary.md" -ForegroundColor Green

Write-Host ""
Write-Host "Evidence collection complete: $runDir" -ForegroundColor Cyan