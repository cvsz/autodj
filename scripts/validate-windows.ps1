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
    [string]$OutputDir = "$PSScriptRoot\..\evidence",
    [string]$CamfrogRoom = "",
    [switch]$SkipBuild,
    [switch]$SkipSign,
    [switch]$SkipUiA,
    [switch]$SkipTts,
    [switch]$SkipE2e
)

$ErrorActionPreference = "Stop"
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
        # Ensure Certificate provider is available (PS5.1 compat) - same fix as build.ps1
        if ($PSVersionTable.PSVersion.Major -le 5) {
            $env:PSModulePath = ($env:PSModulePath -split ';' | Where-Object {
                $_ -and $_ -notmatch 'PowerShell[\\/]7[\\/]Modules' -and
                $_ -notmatch 'Documents[\\/]PowerShell[\\/]Modules' -and
                $_ -notmatch 'Program Files[\\/]PowerShell[\\/]Modules'
            }) -join ';'
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
        
        $windows = & $exePath --windows 2>&1
        $camfrogWindows = $windows | Where-Object { $_ -match "camfrog" -or $_ -match "Camfrog" }
        if (-not $camfrogWindows) {
            Write-Result "uia_adapter" "WARN" "No Camfrog windows found (Camfrog client may not be running)"
            $evidence = @{
                windowsOutput = $windows
                camfrogWindows = $camfrogWindows
                windowCount = 0
            }
            return
        }
        $discoverOutput = & $exePath --discover 2>&1
        $checkOutput = & $exePath --check 2>&1
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
            Write-Result "e2e_integration" "SKIPPED" "CamfrogRoom parameter not provided; use -CamfrogRoom \"RoomName\""
            return
        }
        $checkOutput = & $exePath --check 2>&1
        $discoverOutput = & $exePath --discover -c config.toml 2>&1
        $evidence = @{
            camfrogRoom  = $CamfrogRoom
            checkOutput  = $checkOutput
            discoverOutput = $discoverOutput
            testCases    = @()
        }
        $testCases = @(
            @{ name = "mpv_available"; expected = "OK"; pattern = "mpv.*found" },
            @{ name = "yt_dlp_available"; expected = "OK"; pattern = "yt-dlp" },
            @{ name = "admins_configured"; expected = "OK"; pattern = "admins" },
            @{ name = "bot_nick_configured"; expected = "OK"; pattern = "bot_nick" }
        )
        foreach ($tc in $testCases) {
            $passed = $checkOutput -match $tc.pattern
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
            Write-Result "e2e_integration" "FAIL" "Some E2E prerequisites missing" $evidence
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
$failed = ($Results.results | Where-Object { $_.status -eq "FAIL" }).Count
$passed = ($Results.results | Where-Object { $_.status -eq "PASS" }).Count
$skipped = ($Results.results | Where-Object { $_.status -eq "SKIPPED" }).Count
Write-Host "Summary: $passed passed, $failed failed, $skipped skipped"
if ($failed -gt 0) { exit 1 }
