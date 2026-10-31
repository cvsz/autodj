<#
.SYNOPSIS
    Build NSIS installer for Camfrog AutoDJ
.DESCRIPTION
    This script builds the NSIS installer from the built artifacts in dist/
    Run from PowerShell on Windows (or via wine on Linux)
.NOTES
    Requires: NSIS 3.08+ (makensis.exe in PATH)
    Usage: powershell -ExecutionPolicy Bypass -File scripts/build_installer.ps1
#>

param(
    [string]$Version = "0.2.4",
    [string]$SrcDir = "dist",
    [string]$OutDir = "dist",
    [switch]$Sign
)

$ErrorActionPreference = "Stop"

Write-Host "=== Camfrog AutoDJ Installer Builder ===" -ForegroundColor Cyan
Write-Host "Version: $Version"
Write-Host "Source: $SrcDir"
Write-Host "Output: $OutDir"

# Check for NSIS
$makensis = Get-Command "makensis" -ErrorAction SilentlyContinue
if (-not $makensis) {
    Write-Error "makensis (NSIS) not found in PATH. Install NSIS 3.08+ from https://nsis.sourceforge.io/"
    exit 1
}
Write-Host "Found NSIS: $($makensis.Source)"

# Verify source files exist
$requiredFiles = @(
    "AutoDJ.exe",
    "app.ico",
    "config.example.toml",
    "README.md",
    "CHANGELOG.md",
    "LICENSE.md",
    "install.ps1",
    "uninstall.ps1",
    "run_autodj.py"
)

foreach ($file in $requiredFiles) {
    $path = Join-Path $SrcDir $file
    if (-not (Test-Path $path)) {
        Write-Warning "Missing required file: $path"
    } else {
        Write-Host "  ✓ Found: $file"
    }
}

# Check for optional directories
$optionalDirs = @("camfrog_autodj", "docs", "tools", "tests")
foreach ($dir in $optionalDirs) {
    $path = Join-Path (Get-Location) $dir
    if (Test-Path $path) {
        Write-Host "  ✓ Found directory: $dir"
    }
}

# Create installer.nsi with version substitution
$nsiTemplate = Get-Content "installer.nsi" -Raw
$nsiContent = $nsiTemplate -replace '!define APP_VERSION "0\.2\.3"', "!define APP_VERSION `"$Version`""
$nsiPath = Join-Path $SrcDir "installer.nsi"
$nsiContent | Set-Content -Path $nsiPath -Encoding UTF8

Write-Host "Generated installer.nsi with version $Version"

# Build installer
$installerName = "Camfrog-AutoDJ-Setup-$Version.exe"
$outPath = Join-Path $OutDir $installerName

Write-Host "Building installer: $installerName"
$proc = Start-Process "makensis" -ArgumentList "/DVERSION=$Version", "/DSRCDIR=.", "/DOUTDIR=.", "installer.nsi" -WorkingDirectory $SrcDir -Wait -PassThru -NoNewWindow

if ($proc.ExitCode -ne 0) {
    Write-Error "NSIS build failed with exit code $($proc.ExitCode)"
    exit 1
}

$installerPath = Join-Path $OutDir $installerName
if (Test-Path $installerPath) {
    $sizeMB = [math]::Round((Get-Item $installerPath).Length / 1MB, 1)
    Write-Host "✓ Installer built successfully!" -ForegroundColor Green
    Write-Host "  File: $installerPath"
    Write-Host "  Size: $sizeMB MB"

    # Sign if requested
    if ($Sign) {
        Write-Host "Signing installer..."
        $cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -like "*ZEAZDEV*" } | Select-Object -First 1
        if ($cert) {
            $sig = Set-AuthenticodeSignature -FilePath $installerPath -Certificate $cert -HashAlgorithm SHA256 -TimestampServer "http://timestamp.digicert.com"
            if ($sig.SignerCertificate) {
                Write-Host "  ✓ Signed successfully" -ForegroundColor Green
            } else {
                Write-Warning "Signing failed: $($sig.StatusMessage)"
            }
        } else {
            Write-Warning "No code-signing certificate found"
        }
    }
} else {
    Write-Error "Installer not found at expected location: $installerPath"
    exit 1
}

Write-Host ""
Write-Host "=== Build Complete ===" -ForegroundColor Cyan
Write-Host "Installer: $installerPath"
Write-Host "Version: $Version"