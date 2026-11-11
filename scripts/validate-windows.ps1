<#
.SYNOPSIS
    CamfrogAutoDJ Windows Validation Evidence Collector
.DESCRIPTION
    Collects validation evidence for all 5 blocked items on Windows 11:
    1. Windows Installer Build (NSIS + PyInstaller)
    2. Code Signing (EV Certificate)
    3. UIA Adapter Runtime Validation (Camfrop client)
    4. TTS Runtime Validation (Windows SAPI)
    5. End-to-End Integration Test (Camfrop room + bot account)
.NOTES
    Run as Administrator on Windows 11 host.
    Output: validation-evidence-<timestamp>.json
#>

[CmdletBinding()]
param(
    [string]$OutputDir = "",
    [string]$CamfrogRoom = "",
    [switch]$SkipBuild,
    [switch]$SkipSign,
    [switch]$SkipUiA,
    [switch]$SkipTts,
    [switch]$SkipE2e
)

$ErrorActionPreference = "Stop"
# `make` and the relative config.toml used below must resolve from the repo root, whatever the caller's cwd.
Set-Location (Split-Path $PSScriptRoot -Parent)
# $PSScriptRoot is empty inside a param() default under Windows PowerShell 5.1, which made the
# old default "$PSScriptRoot\..\evidence" resolve to "\..\evidence" (drive root). Default it here.
if (-not $OutputDir) { $OutputDir = Join-Path (Get-Location).Path "evidence" }
if ($PSVersionTable.PSVersion.Major -le 5) {
    # Same PS 5.1 fix as build.ps1: PS7 module dirs on PSModulePath stop Microsoft.PowerShell.Security
    # from loading, so Get-AuthenticodeSignature failed ("module could not be loaded").
    $env:PSModulePath = ($env:PSModulePath -split ';' | Where-Object {
        $_ -and $_ -notmatch 'PowerShell[\\/]7[\\/]Modules' -and
        $_ -notmatch 'Documents[\\/]PowerShell[\\/]Modules' -and
        $_ -notmatch 'Program Files[\\/]PowerShell[\\/]Modules'
    }) -join ';'
}
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$EvidenceFile = "$OutputDir\validation-evidence-$Timestamp.json"
$Results = @{
    timestamp    = (Get-Date).ToString("o")
    windowsBuild = ([System.Environment]::OSVersion.Version).ToString()
    results      = @{}
}

function Write-Result($Test, $Status, $Detail, $Evidence = $null) {
    $Results.results[$Test] = @{
        status   = $Status
        detail   = $Detail
        evidence = $Evidence
        time     = (Get-Date).ToString("o")
    }
    Write-Host "[$Status] $Test - $Detail"
}

function Ensure-Dir($Path) {
    if (-not (Test-Path $Path)) { New-Item -ItemType Directory -Path $Path -Force | Out-Null }
}

# dist\AutoDJ.exe is a windowed (no-console) PyInstaller build: it writes nothing to a pipe or
# redirect, so `& AutoDJ.exe --check 2>&1` always came back empty and every output-based test
# failed. Run the same CLI through the console Python instead and capture its lines.
function Invoke-AutoDJ {
    param([string[]]$CliArgs)
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw "python not found on PATH (needed to capture the AutoDJ CLI output)"
    }
    # Windows PowerShell 5.1 turns native stderr into terminating errors under 'Stop'.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { $out = & python -m camfrog_autodj @CliArgs 2>&1 | ForEach-Object { "$_" } }
    finally { $ErrorActionPreference = $prev }
    return @($out)
}

# --discover WRITES the detected window/control settings into the config it is given, so run it
# against a scratch copy instead of silently rewriting the user's real config.toml.
function New-ScratchConfig {
    $src = if (Test-Path "config.toml") { "config.toml" } else { "config.example.toml" }
    $dst = Join-Path $env:TEMP "autodj-validate-config.toml"
    Copy-Item $src $dst -Force
    return $dst
}

# ============================================
# 1. Windows Installer Build
# ============================================
function Test-InstallerBuild {
    if ($SkipBuild) {
        Write-Result "installer_build" "SKIPPED" "SkipBuild switch set"
        return
    }
    try {
        Ensure-Dir "$OutputDir\build"
        & make build-all SKIP_CHECKS=1
        if ($LASTEXITCODE -ne 0) {
            Write-Result "installer_build" "FAIL" "make build-all failed"
            return
        }
        $exePath = "$PSScriptRoot\..\dist\AutoDJ.exe"
        $installerPath = "$PSScriptRoot\..\dist\Camfrog-AutoDJ-Setup-*.exe"
        $installerFile = Get-ChildItem -Path $installerPath | Select-Object -First 1
        if (-not (Test-Path $exePath)) {
            Write-Result "installer_build" "FAIL" "dist\AutoDJ.exe not found"
            return
        }
        $version = (Get-Item $exePath).VersionInfo.ProductVersion
        $evidence = @{
            exePath        = $exePath
            exeVersion     = $version
            installerPath  = if ($installerFile) { $installerFile.FullName } else { $null }
            installerSize  = if ($installerFile) { $installerFile.Length } else { 0 }
        }
        Write-Result "installer_build" "PASS" "AutoDJ.exe and installer built successfully" $evidence
    } catch {
        Write-Result "installer_build" "FAIL" $_.Exception.Message
    }
}

# ============================================
# 2. Code Signing
# ============================================
function Test-CodeSigning {
    if ($SkipSign) {
        Write-Result "code_signing" "SKIPPED" "SkipSign switch set"
        return
    }
    try {
        $exePath = "$PSScriptRoot\..\dist\AutoDJ.exe"
        if (-not (Test-Path $exePath)) {
            Write-Result "code_signing" "FAIL" "dist\AutoDJ.exe not found. Run build first."
            return
        }
        # Verify existing signature instead of re-signing (build.ps1 already signs)
        $verify = Get-AuthenticodeSignature $exePath
        $evidence = @{
            signatureStatus       = $verify.Status
            signatureMessage      = $verify.StatusMessage
            signerSubject         = if ($verify.SignerCertificate) { $verify.SignerCertificate.Subject } else { "none" }
            timestamp             = if ($verify.TimeStamperCertificate) { $verify.TimeStamperCertificate.Subject } else { "none" }
        }
        if ($verify.Status -eq "Valid" -or $verify.Status -eq "UnknownError") {
            # UnknownError is common for self-signed certs not in trusted store
            Write-Result "code_signing" "PASS" "Authenticode signature present (status: $($verify.Status))" $evidence
        } else {
            Write-Result "code_signing" "WARN" "Signature status: $($verify.Status)" $evidence
        }
    } catch {
        Write-Result "code_signing" "FAIL" $_.Exception.Message
    }
}

# ============================================
# 3. UIA Adapter Runtime Validation
# ============================================
function Test-UiaAdapter {
    if ($SkipUiA) {
        Write-Result "uia_adapter" "SKIPPED" "SkipUiA switch set"
        return
    }
    try {
        # Check if camfrog-autodj is in PATH or use full path
        $exePath = "$PSScriptRoot\..\dist\AutoDJ.exe"
        if (-not (Test-Path $exePath)) {
            Write-Result "uia_adapter" "FAIL" "dist\AutoDJ.exe not found. Run build first."
            return
        }
        
        $windows = Invoke-AutoDJ '--windows'
        $camfrogWindows = $windows | Where-Object { $_ -match "camfrog" -or $_ -match "Camfrog" }
        if (-not $camfrogWindows) {
            $evidence = @{
                windowsOutput = $windows
                camfrogWindows = $camfrogWindows
                windowCount = 0
            }
            # Evidence must be passed to Write-Result; it was built and then dropped before.
            Write-Result "uia_adapter" "WARN" "No Camfrog windows found (Camfrog client may not be running)" $evidence
            return
        }
        $discoverOutput = Invoke-AutoDJ '--discover', '-c', (New-ScratchConfig)
        $checkOutput = Invoke-AutoDJ '--check'
        $evidence = @{
            camfrogWindows    = $camfrogWindows
            discoverOutput    = $discoverOutput
            checkOutput       = $checkOutput
            windowCount       = $camfrogWindows.Count
        }
        if ($checkOutput -match "OK.*Camfrog room window found") {
            Write-Result "uia_adapter" "PASS" "UIA adapter attached to Camfrog room" $evidence
        } else {
            Write-Result "uia_adapter" "WARN" "UIA attached but room window check unclear" $evidence
        }
    } catch {
        Write-Result "uia_adapter" "FAIL" $_.Exception.Message
    }
}

# ============================================
# 4. TTS Runtime Validation
# ============================================
function Test-TtsRuntime {
    if ($SkipTts) {
        Write-Result "tts_runtime" "SKIPPED" "SkipTts switch set"
        return
    }
    try {
        Add-Type -AssemblyName System.Speech
        $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
        $voices = $synth.GetInstalledVoices()
        $voiceList = @()
        foreach ($v in $voices) {
            $voiceList += @{
                name   = $v.VoiceInfo.Name
                gender = $v.VoiceInfo.Gender
                age    = $v.VoiceInfo.Age
                culture= $v.VoiceInfo.Culture.Name
            }
        }
        $testWav = "$env:TEMP\autodj-tts-test.wav"
        $synth.SetOutputToWaveFile($testWav)
        $synth.Speak("Testing TTS text to speech system")
        $synth.SetOutputToDefaultAudioDevice()
        $synth.Dispose()
        $wavExists = Test-Path $testWav
        $evidence = @{
            voices      = $voiceList
            voiceCount  = $voices.Count
            testWavCreated = $wavExists
            testWavPath = $testWav
        }
        if ($voices.Count -gt 0 -and $wavExists) {
            Write-Result "tts_runtime" "PASS" "TTS SAPI available, $($voices.Count) voice(s), WAV created" $evidence
        } else {
            Write-Result "tts_runtime" "FAIL" "TTS SAPI not available or WAV not created" $evidence
        }
    } catch {
        Write-Result "tts_runtime" "FAIL" $_.Exception.Message
    }
}

# ============================================
# 5. End-to-End Integration Test
# ============================================
function Test-E2eIntegration {
    if ($SkipE2e) {
        Write-Result "e2e_integration" "SKIPPED" "SkipE2e switch set"
        return
    }
    try {
        $exePath = "$PSScriptRoot\..\dist\AutoDJ.exe"
        if (-not (Test-Path $exePath)) {
            Write-Result "e2e_integration" "FAIL" "dist\AutoDJ.exe not found. Run build first."
            return
        }
        
        if (-not $CamfrogRoom) {
            Write-Result "e2e_integration" "SKIPPED" 'CamfrogRoom parameter not provided; use -CamfrogRoom "RoomName"'
            return
        }
        $checkOutput = Invoke-AutoDJ '--check'
        $discoverOutput = Invoke-AutoDJ '--discover', '-c', (New-ScratchConfig)
        $evidence = @{
            camfrogRoom  = $CamfrogRoom
            checkOutput  = $checkOutput
            discoverOutput = $discoverOutput
            testCases    = @()
        }
        # --check prints "[ OK ] mpv: <path>" / "[WARN] ..." lines. Match the status tag, not just the
        # word: "admins" also appears in the "[WARN] admins is empty" line and must not count as OK.
        $testCases = @(
            @{ name = "mpv_available";    pattern = '\[ OK \] mpv:' },
            @{ name = "yt_dlp_available"; pattern = '\[ OK \] yt-dlp:' },
            @{ name = "admins_configured"; pattern = '\[WARN\] admins is empty'; invert = $true },
            @{ name = "room_window_found"; pattern = ('\[ OK \] Camfrog room window found.*' + [regex]::Escape($CamfrogRoom)) }
        )
        foreach ($tc in $testCases) {
            $hit = [bool](@($checkOutput | Where-Object { $_ -match $tc.pattern }).Count)
            $passed = if ($tc.invert) { -not $hit } else { $hit }
            $evidence.testCases += @{
                name   = $tc.name
                passed = $passed
                detail = $tc.pattern
            }
        }
        $allPassed = ($evidence.testCases | Where-Object { $_.passed -eq $false }).Count -eq 0
        if ($allPassed) {
            Write-Result "e2e_integration" "PASS" "All E2E prerequisites met" $evidence
        } else {
            $missing = @($evidence.testCases | Where-Object { -not $_.passed } | ForEach-Object { "$($_.name) (looked for /$($_.detail)/ in --check output)" }) -join "; "
            Write-Result "e2e_integration" "FAIL" "Missing E2E prerequisites: $missing" $evidence
        }
    } catch {
        Write-Result "e2e_integration" "FAIL" $_.Exception.Message
    }
}

# ============================================
# Execute all tests
# ============================================
Ensure-Dir $OutputDir
Test-InstallerBuild
Test-CodeSigning
Test-UiaAdapter
Test-TtsRuntime
Test-E2eIntegration

# Save results
$Results | ConvertTo-Json -Depth 10 | Out-File -FilePath $EvidenceFile -Encoding UTF8
Write-Host ""
Write-Host "Evidence saved to: $EvidenceFile"

# Summary
# Piping a hashtable passes it as ONE object, so the old filters always counted 0 (and the
# script could never exit 1). Enumerate the values instead.
$failed = @($Results.results.Values | Where-Object { $_.status -eq "FAIL" }).Count
$passed = @($Results.results.Values | Where-Object { $_.status -eq "PASS" }).Count
$skipped = @($Results.results.Values | Where-Object { $_.status -eq "SKIPPED" }).Count
Write-Host "Summary: $passed passed, $failed failed, $skipped skipped"
if ($failed -gt 0) { exit 1 }
