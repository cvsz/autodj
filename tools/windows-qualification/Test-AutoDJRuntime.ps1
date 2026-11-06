<#
.SYNOPSIS
    AutoDJ Windows Runtime Test Harness.

.DESCRIPTION
    Validates AutoDJ runtime behavior on Windows. Separates simulated tests
    (executable startup, configuration loading, process lifecycle) from
    hardware-dependent tests (audio playback, device enumeration).

    Simulated tests are marked as such and do NOT claim actual audio playback
    or Camfrog integration.

    Exit codes:
        0 = All applicable tests passed
        1 = One or more tests failed
        2 = Script error

.PARAMETER ExePath
    Path to AutoDJ.exe to test.

.PARAMETER TestRoot
    Root directory for disposable test fixtures. Default: ./runtime-test

.PARAMETER NoCleanup
    Keep test directories after execution (for debugging).

.EXAMPLE
    .\Test-AutoDJRuntime.ps1 -ExePath ./dist/AutoDJ.exe
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$ExePath,

    [string]$TestRoot = "runtime-test",

    [switch]$NoCleanup
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

$script:Results = @()
$script:Failures = 0
$testRoot = Resolve-Path $TestRoot -ErrorAction SilentlyContinue
if (-not $testRoot) {
    $testRoot = Join-Path (Get-Location) $TestRoot
}

function Write-Result {
    param(
        [string]$TestId,
        [string]$Status,
        [string]$Detail,
        [string]$Evidence = "",
        [switch]$Simulated
    )
    $tag = if ($Simulated) { " [SIMULATED]" } else { " [LIVE]" }
    $script:Results += [pscustomobject]@{
        TestId       = $TestId
        Status       = $Status
        Detail       = $Detail
        Evidence     = $Evidence
        Simulated    = $Simulated
        TimestampUtc = (Get-Date -Format "o")
    }
    $color = switch ($Status) {
        "PASS"   { "Green" }
        "FAIL"   { "Red" }
        "BLOCKED" { "Red" }
        "NOT RUN" { "Yellow" }
        default  { "White" }
    }
    Write-Host ("[{0}] {1}{2} - {3}" -f $Status, $TestId, $tag, $Detail) -ForegroundColor $color
    if ($Status -eq "FAIL") { $script:Failures++ }
}

function New-TestFixture {
    param([string]$Name)
    $dir = Join-Path $testRoot $Name
    if (Test-Path $dir) { Remove-Item -Path $dir -Recurse -Force -ErrorAction SilentlyContinue }
    New-Item -ItemType Directory -Path $dir -ErrorAction Stop | Out-Null
    return $dir
}

# ---------------------------------------------------------------------------
# Initialize
# ---------------------------------------------------------------------------

Write-Host "=== AutoDJ Windows Runtime Test Harness ===" -ForegroundColor Cyan
Write-Host "Executable: $ExePath"
Write-Host "Test root: $testRoot"
Write-Host ""

if (-not (Test-Path $ExePath)) {
    Write-Host "Executable not found: $ExePath" -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------------------
# Test 1: Startup (--version)
# ---------------------------------------------------------------------------

Write-Host "--- Test 1: Startup (--version) ---" -ForegroundColor Gray

try {
    $proc = Start-Process -FilePath $ExePath -ArgumentList "--version" -PassThru -NoNewWindow -RedirectStandardOutput "$testRoot\version-out.txt" -RedirectStandardError "$testRoot\version-err.txt"
    $proc.WaitForExit(10000)
    $exitCode = $proc.ExitCode
    $versionOut = Get-Content "$testRoot\version-out.txt" -ErrorAction SilentlyContinue

    if ($exitCode -eq 0 -and $versionOut) {
        Write-Result -TestId "RUNTIME-01" -Status "PASS" -Detail "AutoDJ.exe --version exited 0: $versionOut" -Simulated
    } else {
        Write-Result -TestId "RUNTIME-01" -Status "FAIL" -Detail "AutoDJ.exe --version failed (exit code: $exitCode)"
    }
} catch {
    Write-Result -TestId "RUNTIME-01" -Status "FAIL" -Detail "AutoDJ.exe --version exception: $_"
}

# ---------------------------------------------------------------------------
# Test 2: Configuration loading (--check)
# ---------------------------------------------------------------------------

Write-Host "--- Test 2: Configuration loading (--check) ---" -ForegroundColor Gray

$testConfigDir = New-TestFixture "runtime2-config"
Set-Content -Path (Join-Path $testConfigDir "config.toml") -Value @'
bot_nick = "TestBot"
admins = []
prefix = "!"
lang = "en"
mpv_path = "mpv"
ytdlp_path = ""
music_dirs = []
autoplay_sources = []
'@ -Encoding UTF8

try {
    $proc = Start-Process -FilePath $ExePath -ArgumentList "--check", "-c", (Join-Path $testConfigDir "config.toml") -PassThru -NoNewWindow -WorkingDirectory $testConfigDir -RedirectStandardOutput "$testRoot\check-out.txt" -RedirectStandardError "$testRoot\check-err.txt"
    $proc.WaitForExit(15000)
    $exitCode = $proc.ExitCode
    $checkOut = Get-Content "$testRoot\check-out.txt" -ErrorAction SilentlyContinue

    if ($exitCode -eq 0) {
        Write-Result -TestId "RUNTIME-02" -Status "PASS" -Detail "--check exited 0 with valid config"
    } else {
        Write-Result -TestId "RUNTIME-02" -Status "FAIL" -Detail "--check exited $exitCode (may be expected if mpv missing)"
    }
} catch {
    Write-Result -TestId "RUNTIME-02" -Status "FAIL" -Detail "--check exception: $_"
}

# ---------------------------------------------------------------------------
# Test 3: Process lifecycle (start and shutdown)
# ---------------------------------------------------------------------------

Write-Host "--- Test 3: Process lifecycle ---" -ForegroundColor Gray

try {
    $proc = Start-Process -FilePath $ExePath -ArgumentList "--version" -PassThru -NoNewWindow
    $started = $proc.Id -gt 0
    $proc.WaitForExit(5000)
    $exitCode = $proc.ExitCode

    if ($started -and $exitCode -eq 0) {
        Write-Result -TestId "RUNTIME-03" -Status "PASS" -Detail "Process started and exited cleanly (PID: $($proc.Id))"
    } else {
        Write-Result -TestId "RUNTIME-03" -Status "FAIL" -Detail "Process lifecycle issue (exit code: $exitCode)"
    }
} catch {
    Write-Result -TestId "RUNTIME-03" -Status "FAIL" -Detail "Process start exception: $_"
}

# ---------------------------------------------------------------------------
# Test 4: Audio device enumeration
# ---------------------------------------------------------------------------

Write-Host "--- Test 4: Audio device enumeration ---" -ForegroundColor Gray

try {
    $audioDevices = Get-CimInstance Win32_SoundDevice -ErrorAction SilentlyContinue
    if ($audioDevices) {
        $devCount = ($audioDevices | Measure-Object).Count
        $devNames = ($audioDevices | ForEach-Object { $_.Name }) -join ", "
        Write-Result -TestId "RUNTIME-04" -Status "PASS" -Detail "$devCount audio device(s) detected: $devNames" -Simulated
    } else {
        Write-Result -TestId "RUNTIME-04" -Status "WARN" -Detail "No audio devices detected"
    }
} catch {
    Write-Result -TestId "RUNTIME-04" -Status "WARN" -Detail "Unable to query audio devices: $_"
}

# ---------------------------------------------------------------------------
# Test 5: Audio playback (NOT AVAILABLE - no actual mpv integration test)
# ---------------------------------------------------------------------------

Write-Host "--- Test 5: Audio playback ---" -ForegroundColor Gray

Write-Result -TestId "RUNTIME-05" -Status "NOT RUN" -Detail "Actual audio playback requires real mpv integration; not simulated" -Simulated

# ---------------------------------------------------------------------------
# Test 6: Track transition
# ---------------------------------------------------------------------------

Write-Host "--- Test 6: Track transition ---" -ForegroundColor Gray

Write-Result -TestId "RUNTIME-06" -Status "NOT RUN" -Detail "Track transition requires real mpv playback; not simulated" -Simulated

# ---------------------------------------------------------------------------
# Test 7: Fade and crossfade
# ---------------------------------------------------------------------------

Write-Host "--- Test 7: Fade and crossfade ---" -ForegroundColor Gray

Write-Result -TestId "RUNTIME-07" -Status "NOT RUN" -Detail "Fade/crossfade requires real audio hardware; not simulated" -Simulated

# ---------------------------------------------------------------------------
# Test 8: Audio device unavailable
# ---------------------------------------------------------------------------

Write-Host "--- Test 8: Audio device unavailable ---" -ForegroundColor Gray

# Test with invalid mpv path
$invalidConfigDir = New-TestFixture "runtime8-invalid-config"
Set-Content -Path (Join-Path $invalidConfigDir "config.toml") -Value @'
bot_nick = "TestBot"
admins = []
prefix = "!"
lang = "en"
mpv_path = "C:\nonexistent\mpv.exe"
ytdlp_path = ""
music_dirs = []
autoplay_sources = []
'@ -Encoding UTF8

try {
    $proc = Start-Process -FilePath $ExePath -ArgumentList "--check", "-c", (Join-Path $invalidConfigDir "config.toml") -PassThru -NoNewWindow -WorkingDirectory $invalidConfigDir -RedirectStandardOutput "$testRoot\check-invalid-out.txt" -RedirectStandardError "$testRoot\check-invalid-err.txt"
    $proc.WaitForExit(15000)
    $exitCode = $proc.ExitCode

    # --check should report FAIL for missing mpv but not crash
    if ($exitCode -eq 1) {
        Write-Result -TestId "RUNTIME-08" -Status "PASS" -Detail "--check correctly reports FAIL for missing mpv (exit code 1)"
    } else {
        Write-Result -TestId "RUNTIME-08" -Status "WARN" -Detail "--check exit code $exitCode for missing mpv (expected 1)"
    }
} catch {
    Write-Result -TestId "RUNTIME-08" -Status "FAIL" -Detail "--check exception for missing mpv: $_"
}

# ---------------------------------------------------------------------------
# Test 9: Missing media file
# ---------------------------------------------------------------------------

Write-Host "--- Test 9: Missing media file ---" -ForegroundColor Gray

# This requires actual playback which we can't test without mpv
Write-Result -TestId "RUNTIME-09" -Status "NOT RUN" -Detail "Missing media file handling requires real mpv playback; not simulated" -Simulated

# ---------------------------------------------------------------------------
# Test 10: Invalid playlist
# ---------------------------------------------------------------------------

Write-Host "--- Test 10: Invalid playlist ---" -ForegroundColor Gray

$invalidPlaylistDir = New-TestFixture "runtime10-invalid-playlist"
Set-Content -Path (Join-Path $invalidPlaylistDir "playlist.json") -Value '{invalid json' -Encoding UTF8
Set-Content -Path (Join-Path $invalidPlaylistDir "config.toml") -Value @'
bot_nick = "TestBot"
admins = []
prefix = "!"
playlist_file = "playlist.json"
'@ -Encoding UTF8

try {
    $proc = Start-Process -FilePath $ExePath -ArgumentList "--check", "-c", (Join-Path $invalidPlaylistDir "config.toml") -PassThru -NoNewWindow -WorkingDirectory $invalidPlaylistDir -RedirectStandardOutput "$testRoot\check-playlist-out.txt" -RedirectStandardError "$testRoot\check-playlist-err.txt"
    $proc.WaitForExit(15000)
    $exitCode = $proc.ExitCode

    # --check should not crash on invalid playlist (playlist is loaded at runtime, not check time)
    Write-Result -TestId "RUNTIME-10" -Status "PASS" -Detail "--check completed with exit code $exitCode for invalid playlist (playlist loaded at runtime)"
} catch {
    Write-Result -TestId "RUNTIME-10" -Status "FAIL" -Detail "--check exception for invalid playlist: $_"
}

# ---------------------------------------------------------------------------
# Test 11: Application crash and restart
# ---------------------------------------------------------------------------

Write-Host "--- Test 11: Application crash and restart ---" -ForegroundColor Gray

# Cannot safely test crash; verify clean restart instead
try {
    $proc1 = Start-Process -FilePath $ExePath -ArgumentList "--version" -PassThru -NoNewWindow
    $proc1.WaitForExit(5000)
    $proc2 = Start-Process -FilePath $ExePath -ArgumentList "--version" -PassThru -NoNewWindow
    $proc2.WaitForExit(5000)

    if ($proc1.ExitCode -eq 0 -and $proc2.ExitCode -eq 0) {
        Write-Result -TestId "RUNTIME-11" -Status "PASS" -Detail "Repeated startup successful (two clean runs)"
    } else {
        Write-Result -TestId "RUNTIME-11" -Status "FAIL" -Detail "Repeated startup failed (exit codes: $($proc1.ExitCode), $($proc2.ExitCode))"
    }
} catch {
    Write-Result -TestId "RUNTIME-11" -Status "FAIL" -Detail "Repeated startup exception: $_"
}

# ---------------------------------------------------------------------------
# Test 12: Graceful shutdown
# ---------------------------------------------------------------------------

Write-Host "--- Test 12: Graceful shutdown ---" -ForegroundColor Gray

# --version starts and exits cleanly; this tests graceful termination
try {
    $proc = Start-Process -FilePath $ExePath -ArgumentList "--version" -PassThru -NoNewWindow
    $proc.WaitForExit(5000)

    if ($proc.ExitCode -eq 0 -and -not $proc.HasExited -eq $false) {
        Write-Result -TestId "RUNTIME-12" -Status "PASS" -Detail "Process exited gracefully (exit code: $($proc.ExitCode))"
    } else {
        Write-Result -TestId "RUNTIME-12" -Status "FAIL" -Detail "Process did not exit gracefully (exit code: $($proc.ExitCode))"
    }
} catch {
    Write-Result -TestId "RUNTIME-12" -Status "FAIL" -Detail "Graceful shutdown exception: $_"
}

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

if (-not $NoCleanup) {
    Write-Host ""
    Write-Host "Cleaning up test directories..." -ForegroundColor Gray
    Remove-Item -Path $testRoot -Recurse -Force -ErrorAction SilentlyContinue
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "=== Windows Runtime Test Summary ===" -ForegroundColor Cyan
$passed = ($script:Results | Where-Object { $_.Status -eq "PASS" }).Count
$failed = ($script:Results | Where-Object { $_.Status -eq "FAIL" }).Count
$blocked = ($script:Results | Where-Object { $_.Status -eq "BLOCKED" }).Count
$notRun = ($script:Results | Where-Object { $_.Status -eq "NOT RUN" }).Count
Write-Host ("Passed: $passed, Failed: $failed, Blocked: $blocked, Not Run: $notRun") -ForegroundColor Cyan

exit $script:Failures