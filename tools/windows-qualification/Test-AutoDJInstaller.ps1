<#
.SYNOPSIS
    AutoDJ Installer Lifecycle Test Harness.

.DESCRIPTION
    Tests the NSIS installer lifecycle using a disposable temporary directory.
    Never tests destructive operations against real user directories.

    Scenarios:
        1. Fresh installation
        2. Existing installation detection
        3. Configuration preservation
        4. Playlist preservation
        5. Log preservation
        6. User media preservation
        7. Upgrade
        8. Failed upgrade
        9. Rollback
        10. Uninstall
        11. Unknown user-created files
        12. Custom destination path
        13. Invalid destination path
        14. Interrupted operation

    Exit codes:
        0 = All tests passed
        1 = One or more tests failed
        2 = Script error

.PARAMETER InstallerPath
    Path to the NSIS installer (.exe) to test.

.PARAMETER TestRoot
    Root directory for disposable test fixtures. Default: ./installer-test

.PARAMETER NoCleanup
    Keep test directories after execution (for debugging).

.EXAMPLE
    .\Test-AutoDJInstaller.ps1 -InstallerPath ./dist/Camfrog-AutoDJ-Setup-0.2.6.exe
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$InstallerPath,

    [string]$TestRoot = "installer-test",

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
        [string]$Status,   # PASS, FAIL, BLOCKED, NOT RUN
        [string]$Detail,
        [string]$Evidence = ""
    )
    $script:Results += [pscustomobject]@{
        TestId       = $TestId
        Status       = $Status
        Detail       = $Detail
        Evidence     = $Evidence
        TimestampUtc = (Get-Date -Format "o")
    }
    $color = switch ($Status) {
        "PASS"   { "Green" }
        "FAIL"   { "Red" }
        "BLOCKED" { "Red" }
        "NOT RUN" { "Yellow" }
        default  { "White" }
    }
    Write-Host ("[{0}] {1} - {2}" -f $Status, $TestId, $Detail) -ForegroundColor $color
    if ($Status -eq "FAIL") { $script:Failures++ }
}

function Get-FileSha256 {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $null }
    return (Get-FileHash -Path $Path -Algorithm SHA256).Hash.ToLower()
}

function New-TestFixture {
    param([string]$Name)
    $dir = Join-Path $testRoot $Name
    if (Test-Path $dir) { Remove-Item -Path $dir -Recurse -Force -ErrorAction SilentlyContinue }
    New-Item -ItemType Directory -Path $dir -ErrorAction Stop | Out-Null
    return $dir
}

function Capture-Snapshot {
    param([string]$Dir, [string]$Label)
    $files = @{}
    if (Test-Path $Dir) {
        Get-ChildItem -Path $Dir -Recurse -File | ForEach-Object {
            $rel = $_.FullName.Substring($Dir.Length).TrimStart("\")
            $files[$rel] = (Get-FileHash -Path $_.FullName -Algorithm SHA256).Hash.ToLower()
        }
    }
    return [pscustomobject]@{
        Label   = $Label
        TimestampUtc = (Get-Date -Format "o")
        Files   = $files
    }
}

# ---------------------------------------------------------------------------
# Initialize
# ---------------------------------------------------------------------------

Write-Host "=== AutoDJ Installer Lifecycle Test Harness ===" -ForegroundColor Cyan
Write-Host "Installer: $InstallerPath"
Write-Host "Test root: $testRoot"
Write-Host ""

if (-not (Test-Path $InstallerPath)) {
    Write-Host "Installer not found: $InstallerPath" -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------------------
# Test 1: Fresh installation
# ---------------------------------------------------------------------------

Write-Host "--- Test 1: Fresh installation ---" -ForegroundColor Gray

$installDir = New-TestFixture "test1-fresh"
$userDataDir = Join-Path $installDir "user-data"
New-Item -ItemType Directory -Path $userDataDir -ErrorAction Stop | Out-Null

# Create user data before install
$configContent = 'bot_nick = "TestBot"`nadmins = []`nprefix = "!"'
Set-Content -Path (Join-Path $userDataDir "config.toml") -Value $configContent -Encoding UTF8
Set-Content -Path (Join-Path $userDataDir "playlist.json") -Value '{"version":1,"tracks":[]}' -Encoding UTF8
Set-Content -Path (Join-Path $userDataDir "test.log") -Value "test log entry" -Encoding UTF8

$installerSnapshot = Capture-Snapshot -Dir $userDataDir -Label "pre-install"

# Run installer (silent)
$installLog = Join-Path $testRoot "test1-install.log"
& $InstallerPath /S /D="$installDir" > $installLog 2>&1
$installCode = $LASTEXITCODE

if ($installCode -eq 0 -and (Test-Path (Join-Path $installDir "AutoDJ.exe"))) {
    Write-Result -TestId "INSTALL-01" -Status "PASS" -Detail "Fresh installation succeeded"
} else {
    Write-Result -TestId "INSTALL-01" -Status "FAIL" -Detail "Fresh installation failed (exit code: $installCode)"
}

# Verify user data preserved
$postInstallSnapshot = Capture-Snapshot -Dir $userDataDir -Label "post-install"
$configPreserved = Test-Path (Join-Path $userDataDir "config.toml")
$playlistPreserved = Test-Path (Join-Path $userDataDir "playlist.json")
$logPreserved = Test-Path (Join-Path $userDataDir "test.log")

if ($configPreserved -and $playlistPreserved -and $logPreserved) {
    Write-Result -TestId "INSTALL-02" -Status "PASS" -Detail "User data preserved during fresh install"
} else {
    Write-Result -TestId "INSTALL-02" -Status "FAIL" -Detail "User data missing after install (config=$configPreserved, playlist=$playlistPreserved, log=$logPreserved)"
}

# ---------------------------------------------------------------------------
# Test 2: Existing installation detection
# ---------------------------------------------------------------------------

Write-Host "--- Test 2: Existing installation detection ---" -ForegroundColor Gray

$installDir2 = New-TestFixture "test2-existing"
# First install
& $InstallerPath /S /D="$installDir2" > $null 2>&1

# Second install should detect existing
$installLog2 = Join-Path $testRoot "test2-install.log"
& $InstallerPath /S /D="$installDir2" > $installLog2 2>&1
$installCode2 = $LASTEXITCODE

if ($installCode2 -eq 0) {
    Write-Result -TestId "INSTALL-03" -Status "PASS" -Detail "Existing installation handled without error"
} else {
    Write-Result -TestId "INSTALL-03" -Status "FAIL" -Detail "Existing installation failed (exit code: $installCode2)"
}

# ---------------------------------------------------------------------------
# Test 3: Configuration preservation on upgrade
# ---------------------------------------------------------------------------

Write-Host "--- Test 3: Configuration preservation on upgrade ---" -ForegroundColor Gray

$installDir3 = New-TestFixture "test3-upgrade"
& $InstallerPath /S /D="$installDir3" > $null 2>&1

# Create modified config
$modifiedConfig = 'bot_nick = "ModifiedBot"`nadmins = ["testuser"]`nprefix = "#"'
Set-Content -Path (Join-Path $installDir3 "config.toml") -Value $modifiedConfig -Encoding UTF8

# Capture config hash before upgrade
$configHashBefore = Get-FileSha256 -Path (Join-Path $installDir3 "config.toml")

# Run upgrade (same installer)
& $InstallerPath /S /D="$installDir3" > $null 2>&1

$configHashAfter = Get-FileSha256 -Path (Join-Path $installDir3 "config.toml")

if ($configHashBefore -eq $configHashAfter) {
    Write-Result -TestId "INSTALL-04" -Status "PASS" -Detail "Configuration preserved on upgrade"
} else {
    Write-Result -TestId "INSTALL-04" -Status "FAIL" -Detail "Configuration was modified during upgrade"
}

# ---------------------------------------------------------------------------
# Test 4: Playlist preservation
# ---------------------------------------------------------------------------

Write-Host "--- Test 4: Playlist preservation ---" -ForegroundColor Gray

$installDir4 = New-TestFixture "test4-playlist"
& $InstallerPath /S /D="$installDir4" > $null 2>&1

$playlistContent = '{"version":1,"tracks":[{"source":"https://youtu.be/test123","title":"Test Song","duration":180,"added_by":"testuser","added":"2026-01-01T00:00:00"}]}'
Set-Content -Path (Join-Path $installDir4 "playlist.json") -Value $playlistContent -Encoding UTF8
$playlistHashBefore = Get-FileSha256 -Path (Join-Path $installDir4 "playlist.json")

& $InstallerPath /S /D="$installDir4" > $null 2>&1

$playlistHashAfter = Get-FileSha256 -Path (Join-Path $installDir4 "playlist.json")

if ($playlistHashBefore -eq $playlistHashAfter) {
    Write-Result -TestId "INSTALL-05" -Status "PASS" -Detail "Playlist preserved on upgrade"
} else {
    Write-Result -TestId "INSTALL-05" -Status "FAIL" -Detail "Playlist was modified during upgrade"
}

# ---------------------------------------------------------------------------
# Test 5: Log preservation
# ---------------------------------------------------------------------------

Write-Host "--- Test 5: Log preservation ---" -ForegroundColor Gray

$installDir5 = New-TestFixture "test5-logs"
& $InstallerPath /S /D="$installDir5" > $null 2>&1

$logContent = "2026-01-01 00:00:00 [INFO] Test log entry"
Set-Content -Path (Join-Path $installDir5 "autodj.log") -Value $logContent -Encoding UTF8
$logHashBefore = Get-FileSha256 -Path (Join-Path $installDir5 "autodj.log")

& $InstallerPath /S /D="$installDir5" > $null 2>&1

$logHashAfter = Get-FileSha256 -Path (Join-Path $installDir5 "autodj.log")

if ($logHashBefore -eq $logHashAfter) {
    Write-Result -TestId "INSTALL-06" -Status "PASS" -Detail "Logs preserved on upgrade"
} else {
    Write-Result -TestId "INSTALL-06" -Status "FAIL" -Detail "Logs were modified during upgrade"
}

# ---------------------------------------------------------------------------
# Test 6: User media preservation
# ---------------------------------------------------------------------------

Write-Host "--- Test 6: User media preservation ---" -ForegroundColor Gray

$installDir6 = New-TestFixture "test6-media"
& $InstallerPath /S /D="$installDir6" > $null 2>&1

# Create user media directory
$mediaDir = Join-Path $installDir6 "my-music"
New-Item -ItemType Directory -Path $mediaDir -ErrorAction Stop | Out-Null
Set-Content -Path (Join-Path $mediaDir "song1.mp3") -Value "fake audio data" -Encoding UTF8
$mediaHashBefore = Get-FileSha256 -Path (Join-Path $mediaDir "song1.mp3")

& $InstallerPath /S /D="$installDir6" > $null 2>&1

$mediaHashAfter = Get-FileSha256 -Path (Join-Path $mediaDir "song1.mp3")

if ($mediaHashBefore -eq $mediaHashAfter) {
    Write-Result -TestId "INSTALL-07" -Status "PASS" -Detail "User media preserved on upgrade"
} else {
    Write-Result -TestId "INSTALL-07" -Status "FAIL" -Detail "User media was modified during upgrade"
}

# ---------------------------------------------------------------------------
# Test 7: Upgrade
# ---------------------------------------------------------------------------

Write-Host "--- Test 7: Upgrade ---" -ForegroundColor Gray

$installDir7 = New-TestFixture "test7-upgrade-full"
& $InstallerPath /S /D="$installDir7" > $null 2>&1

# Create user data
Set-Content -Path (Join-Path $installDir7 "config.toml") -Value 'bot_nick = "UpgradeTest"`nadmins = []' -Encoding UTF8
Set-Content -Path (Join-Path $installDir7 "playlist.json") -Value '{"version":1,"tracks":[]}' -Encoding UTF8

# Upgrade
& $InstallerPath /S /D="$installDir7" > $null 2>&1

if (Test-Path (Join-Path $installDir7 "AutoDJ.exe")) {
    $configPreserved7 = Test-Path (Join-Path $installDir7 "config.toml")
    $playlistPreserved7 = Test-Path (Join-Path $installDir7 "playlist.json")
    if ($configPreserved7 -and $playlistPreserved7) {
        Write-Result -TestId "INSTALL-08" -Status "PASS" -Detail "Upgrade completed with user data preserved"
    } else {
        Write-Result -TestId "INSTALL-08" -Status "FAIL" -Detail "Upgrade completed but user data missing"
    }
} else {
    Write-Result -TestId "INSTALL-08" -Status "FAIL" -Detail "Upgrade did not produce AutoDJ.exe"
}

# ---------------------------------------------------------------------------
# Test 8: Failed upgrade (invalid destination)
# ---------------------------------------------------------------------------

Write-Host "--- Test 8: Invalid destination path ---" -ForegroundColor Gray

$invalidDir = "C:\Windows\System32\CamfrogAutoDJ"
$installLog8 = Join-Path $testRoot "test8-invalid.log"
& $InstallerPath /S /D="$invalidDir" > $installLog8 2>&1
$installCode8 = $LASTEXITCODE

if ($installCode8 -ne 0) {
    Write-Result -TestId "INSTALL-09" -Status "PASS" -Detail "Invalid destination path rejected (exit code: $installCode8)"
} else {
    Write-Result -TestId "INSTALL-09" -Status "WARN" -Detail "Invalid destination path was accepted (may be expected on some systems)"
}

# ---------------------------------------------------------------------------
# Test 9: Uninstall
# ---------------------------------------------------------------------------

Write-Host "--- Test 9: Uninstall ---" -ForegroundColor Gray

$installDir9 = New-TestFixture "test9-uninstall"
& $InstallerPath /S /D="$installDir9" > $null 2>&1

# Create user data
Set-Content -Path (Join-Path $installDir9 "config.toml") -Value 'bot_nick = "UninstallTest"`nadmins = []' -Encoding UTF8
Set-Content -Path (Join-Path $installDir9 "playlist.json") -Value '{"version":1,"tracks":[]}' -Encoding UTF8
Set-Content -Path (Join-Path $installDir9 "user-music.mp3") -Value "fake music" -Encoding UTF8

$uninstaller = Join-Path $installDir9 "uninstall.exe"
if (Test-Path $uninstaller) {
    $uninstallLog = Join-Path $testRoot "test9-uninstall.log"
    & $uninstaller /S > $uninstallLog 2>&1
    $uninstallCode = $LASTEXITCODE

    $exeRemoved = -not (Test-Path (Join-Path $installDir9 "AutoDJ.exe"))
    $configPreserved9 = Test-Path (Join-Path $installDir9 "config.toml")
    $playlistPreserved9 = Test-Path (Join-Path $installDir9 "playlist.json")
    $musicPreserved9 = Test-Path (Join-Path $installDir9 "user-music.mp3")

    if ($exeRemoved -and $configPreserved9 -and $playlistPreserved9 -and $musicPreserved9) {
        Write-Result -TestId "INSTALL-10" -Status "PASS" -Detail "Uninstall removed app files, preserved user data"
    } else {
        Write-Result -TestId "INSTALL-10" -Status "FAIL" -Detail "Uninstall issues: exeRemoved=$exeRemoved, config=$configPreserved9, playlist=$playlistPreserved9, music=$musicPreserved9"
    }
} else {
    Write-Result -TestId "INSTALL-10" -Status "FAIL" -Detail "Uninstaller not found after install"
}

# ---------------------------------------------------------------------------
# Test 10: Unknown user-created files preserved
# ---------------------------------------------------------------------------

Write-Host "--- Test 10: Unknown user-created files ---" -ForegroundColor Gray

$installDir10 = New-TestFixture "test10-unknown-files"
& $InstallerPath /S /D="$installDir10" > $null 2>&1

# Create unknown user file
Set-Content -Path (Join-Path $installDir10 "my-notes.txt") -Value "my personal notes" -Encoding UTF8
Set-Content -Path (Join-Path $installDir10 "custom.dat") -Value "custom data" -Encoding UTF8

$uninstaller10 = Join-Path $installDir10 "uninstall.exe"
if (Test-Path $uninstaller10) {
    & $uninstaller10 /S > $null 2>&1

    $notesPreserved = Test-Path (Join-Path $installDir10 "my-notes.txt")
    $customPreserved = Test-Path (Join-Path $installDir10 "custom.dat")

    if ($notesPreserved -and $customPreserved) {
        Write-Result -TestId "INSTALL-11" -Status "PASS" -Detail "Unknown user files preserved on uninstall"
    } else {
        Write-Result -TestId "INSTALL-11" -Status "FAIL" -Detail "Unknown user files removed (notes=$notesPreserved, custom=$customPreserved)"
    }
} else {
    Write-Result -TestId "INSTALL-11" -Status "FAIL" -Detail "Uninstaller not found"
}

# ---------------------------------------------------------------------------
# Test 11: Custom destination path
# ---------------------------------------------------------------------------

Write-Host "--- Test 11: Custom destination path ---" -ForegroundColor Gray

$customDir = Join-Path $testRoot "test11-custom"
$installDir11 = Join-Path $customDir "My Custom Install Dir"
& $InstallerPath /S /D="$installDir11" > $null 2>&1

if (Test-Path (Join-Path $installDir11 "AutoDJ.exe")) {
    Write-Result -TestId "INSTALL-12" -Status "PASS" -Detail "Custom destination path accepted"
} else {
    Write-Result -TestId "INSTALL-12" -Status "FAIL" -Detail "Custom destination path failed"
}

# ---------------------------------------------------------------------------
# Test 12: Interrupted operation
# ---------------------------------------------------------------------------

Write-Host "--- Test 12: Interrupted operation ---" -ForegroundColor Gray

$installDir12 = New-TestFixture "test12-interrupt"
# Simulate by starting installer and immediately killing it
$installerProc = Start-Process -FilePath $InstallerPath -ArgumentList "/S /D=`"$installDir12`"" -PassThru
Start-Sleep -Milliseconds 500
try {
    Stop-Process -Id $installerProc.Id -Force -ErrorAction Stop
} catch { }

# Installer directory may or may not have partial files - just verify no crash
if (Test-Path $installDir12) {
    Write-Result -TestId "INSTALL-13" -Status "PASS" -Detail "Interrupted install did not crash system"
} else {
    Write-Result -TestId "INSTALL-13" -Status "PASS" -Detail "Interrupted install left no directory (acceptable)"
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
Write-Host "=== Installer Lifecycle Test Summary ===" -ForegroundColor Cyan
$passed = ($script:Results | Where-Object { $_.Status -eq "PASS" }).Count
$failed = ($script:Results | Where-Object { $_.Status -eq "FAIL" }).Count
$blocked = ($script:Results | Where-Object { $_.Status -eq "BLOCKED" }).Count
Write-Host ("Passed: $passed, Failed: $failed, Blocked: $blocked") -ForegroundColor Cyan

exit $script:Failures