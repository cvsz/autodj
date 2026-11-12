<#
.SYNOPSIS
    Build NSIS installer for CamfrogAutoDJ
.DESCRIPTION
    This script builds the NSIS installer from the built artifacts in dist/
    Run from PowerShell on Windows (or via wine on Linux)
.NOTES
    Requires: NSIS 3.08+ (makensis.exe in PATH)
    Usage: powershell -ExecutionPolicy Bypass -File scripts/build_installer.ps1
#>

param(
    [string]$Version = "0.3.0",
    [string]$SrcDir = "dist",
    [string]$OutDir = "dist",
    [switch]$Sign
)

$ErrorActionPreference = "Stop"

# Ensure Certificate provider is available (PS5.1 compat)
if ($PSVersionTable.PSVersion.Major -le 5) {
    $env:PSModulePath = ($env:PSModulePath -split ';' | Where-Object {
        $_ -and $_ -notmatch 'PowerShell[\\/]7[\\/]Modules' -and
        $_ -notmatch 'Documents[\\/]PowerShell[\\/]Modules' -and
        $_ -notmatch 'Program Files[\\/]PowerShell[\\/]Modules'
    }) -join ';'
}

Write-Host "=== CamfrogAutoDJ Installer Builder ===" -ForegroundColor Cyan
Write-Host "Version: $Version"
Write-Host "Source: $SrcDir"
Write-Host "Output: $OutDir"

# Check for NSIS
$makensis = Get-Command "makensis" -ErrorAction SilentlyContinue
if (-not $makensis) {
    # Check common install locations
    $commonPaths = @(
        "C:\Program Files (x86)\NSIS\makensis.exe",
        "C:\Program Files\NSIS\makensis.exe"
    )
    foreach ($path in $commonPaths) {
        if (Test-Path $path) {
            $makensis = $path
            Write-Host "Found NSIS at: $path" -ForegroundColor Yellow
            break
        }
    }
}
if (-not $makensis) {
    Write-Error "makensis (NSIS) not found in PATH or common locations. Install NSIS 3.08+ from https://nsis.sourceforge.io/"
    exit 1
}
Write-Host "Found NSIS: $makensis"

# Verify source files exist
$requiredFiles = @(
    "AutoDJ.exe",
    "app.ico",
    "config.example.toml",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    "install.ps1",
    "run_autodj.py"
)

foreach ($file in $requiredFiles) {
    $path = Join-Path $SrcDir $file
    if (-not (Test-Path $path)) {
        Write-Warning "Missing required file: $path"
    } else {
        Write-Host "  Found: $file"
    }
}

# Check for optional directories
$optionalDirs = @("camfrog_autodj", "docs", "tools", "tests")
foreach ($dir in $optionalDirs) {
    $path = Join-Path (Get-Location) $dir
    if (Test-Path $path) {
        Write-Host "  Found directory: $dir"
    }
}

# Render installer.nsi with the real version.  The shared renderer is also used
# by scripts/build_installer_linux.sh so the substitution rule cannot drift.
$nsiPath = Join-Path $SrcDir "installer.nsi"
$renderer = Join-Path $PSScriptRoot "render_installer_nsi.py"
& python $renderer --version $Version --input "installer.nsi" --output $nsiPath
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to render installer.nsi with version $Version (is python on PATH?)"
    exit 1
}

Write-Host "Generated installer.nsi with version $Version"

# Build installer
$installerName = "Camfrog-AutoDJ-Setup-$Version.exe"

Write-Host "Building installer: $installerName"
# Run makensis from repo root so installer.nsi paths work correctly.
# -NOCD keeps that working directory even though the rendered script lives in
# $SrcDir; /DAPP_VERSION overrides the !define /IfNDef default as a backstop.
$repoRoot = (Get-Location).Path
$renderedNsi = (Resolve-Path $nsiPath).Path
$proc = Start-Process $makensis -ArgumentList "-NOCD", "/DAPP_VERSION=$Version", "/DSRCDIR=.", "/DOUTDIR=.", $renderedNsi -WorkingDirectory $repoRoot -Wait -PassThru -NoNewWindow

if ($proc.ExitCode -ne 0) {
    Write-Error "NSIS build failed with exit code $($proc.ExitCode)"
    exit 1
}

$installerPath = Join-Path $repoRoot $installerName
$outInstallerPath = Join-Path $OutDir $installerName

# Copy installer to output directory if it was created in repo root
if ((Test-Path $installerPath) -and (-not (Test-Path $outInstallerPath))) {
    Copy-Item $installerPath $outInstallerPath -Force
    $installerPath = $outInstallerPath
} elseif (Test-Path $outInstallerPath) {
    $installerPath = $outInstallerPath
}

if (Test-Path $installerPath) {
    $sizeMB = [math]::Round((Get-Item $installerPath).Length / 1MB, 1)
    Write-Host "Installer built successfully!" -ForegroundColor Green
    Write-Host "  File: $installerPath"
    Write-Host "  Size: $sizeMB MB"

    # Sign if requested
    if ($Sign) {
        Write-Host "Signing installer..."
        $cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -like "*ZEAZDEV*" } | Select-Object -First 1
        if ($cert) {
            $sig = Set-AuthenticodeSignature -FilePath $installerPath -Certificate $cert -HashAlgorithm SHA256 -TimestampServer "http://timestamp.digicert.com"
            if ($sig.SignerCertificate) {
                Write-Host "  Signed successfully" -ForegroundColor Green
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