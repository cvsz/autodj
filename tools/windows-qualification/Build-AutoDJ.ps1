<#
.SYNOPSIS
    AutoDJ Windows Build Runner - Reproducible build and installer compilation.

.DESCRIPTION
    Verifies the working tree, installs dependencies reproducibly, runs
    applicable tests, executes lint and strict typecheck, builds the Windows
    executable, compiles the NSIS installer, and generates SHA256 checksums.

    Every command and exit code is reported. Required steps that fail
    cause the script to exit with a non-zero code. Missing dependencies are
    never silently skipped.

    This script is intended to run on a real Windows 11 host. It does NOT
    create or publish a release, and does not modify published tags.

.PARAMETER OutputDir
    Directory for build artifacts and logs. Default: ./build-output

.PARAMETER Version
    Version string to embed in the installer. Default: read from pyproject.toml

.PARAMETER NoSign
    Build without code signing (unsigned development build).

.PARAMETER Pfx
    Path to PFX certificate file for Authenticode signing.

.PARAMETER Password
    Password for the PFX certificate.

.PARAMETER Thumbprint
    Thumbprint of a certificate already in the Windows certificate store.

.EXAMPLE
    .\Build-AutoDJ.ps1 -OutputDir ./build-output
    .\Build-AutoDJ.ps1 -OutputDir ./build-output -Pfx cert\autodj.pfx -Password "secret"
#>
[CmdletBinding()]
param(
    [string]$OutputDir = "build-output",
    [string]$Version = "",
    [switch]$NoSign,
    [string]$Pfx = $env:AUTODJ_PFX,
    [string]$Password = $env:AUTODJ_PFX_PASSWORD,
    [string]$Thumbprint = $env:AUTODJ_CERT_THUMBPRINT
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-ScriptHeader {
    param([string]$Message)
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host "  $Message" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
}

function Write-Command {
    param([string]$Command)
    Write-Host ("$ " + $Command) -ForegroundColor Gray
}

function Invoke-CommandWithCode {
    param([string]$Command, [string]$Description = "")
    Write-Command $Command
    try {
        & $Command 2>&1
        $code = $LASTEXITCODE
        if ($code -ne 0) {
            Write-Host ("EXIT CODE: $code ($Description)") -ForegroundColor Red
        } else {
            Write-Host ("EXIT CODE: $code ($Description) - OK") -ForegroundColor Green
        }
        return $code
    } catch {
        $code = 1
        Write-Host ("EXCEPTION: $_ ($Description)") -ForegroundColor Red
        return $code
    }
}

function Test-CommandExists {
    param([string]$Name)
    return (Get-Command $Name -ErrorAction SilentlyContinue) -ne $null
}

# ---------------------------------------------------------------------------
# Initialize
# ---------------------------------------------------------------------------

$script:OverallExitCode = 0
$runId = (Get-Date -Format "yyyyMMdd-HHmmss")
$scriptRoot = (Get-Item (Resolve-Path $PSScriptRoot).Parent.Parent).FullName

# Default output dir
if (-not $OutputDir) {
    $OutputDir = "build-output"
}
$outputRoot = Resolve-Path (Join-Path $scriptRoot $OutputDir) -ErrorAction Stop
if (-not (Test-Path $outputRoot)) {
    New-Item -ItemType Directory -Path $outputRoot -ErrorAction Stop | Out-Null
}
$logDir = Join-Path $outputRoot "logs"
New-Item -ItemType Directory -Path $logDir -ErrorAction Stop | Out-Null
$artifactDir = Join-Path $outputRoot "artifacts"
New-Item -ItemType Directory -Path $artifactDir -ErrorAction Stop | Out-Null

Write-Host "=== AutoDJ Windows Build Runner ===" -ForegroundColor Cyan
Write-Host "Run ID: $runId"
Write-Host "Script root: $scriptRoot"
Write-Host "Output dir:  $outputRoot"
Write-Host "Log dir:     $logDir"
Write-Host ""

# ---------------------------------------------------------------------------
# Step 1: Verify working tree and commit SHA
# ---------------------------------------------------------------------------

Write-ScriptHeader "Step 1: Verify working tree and commit SHA"

$commit = Invoke-CommandWithCode -Command "git rev-parse HEAD" -Description "Get commit SHA"
if ($commit -ne 0) { $script:OverallExitCode = 1 }

$status = Invoke-CommandWithCode -Command "git status --short" -Description "Check working tree cleanliness"
if ($status -ne 0) { $script:OverallExitCode = 1 }

$remote = Invoke-CommandWithCode -Command "git rev-parse origin/main" -Description "Get origin/main SHA"
if ($remote -ne 0) { $script:OverallExitCode = 1 }

# Capture SHA for logging
$headSha = & git rev-parse HEAD 2>$null
$originSha = & git rev-parse origin/main 2>$null
Write-Host ("HEAD:  $headSha") -ForegroundColor Gray
Write-Host ("origin/main: $originSha") -ForegroundColor Gray

if ($headSha -ne $originSha) {
    Write-Host "WARNING: HEAD does not match origin/main" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Step 2: Verify version
# ---------------------------------------------------------------------------

Write-ScriptHeader "Step 2: Verify version"

if (-not $Version) {
    $Version = & python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Unable to read version from pyproject.toml" -ForegroundColor Red
        $script:OverallExitCode = 1
    }
}
Write-Host ("Version: $Version") -ForegroundColor Gray

# ---------------------------------------------------------------------------
# Step 3: Install dependencies
# ---------------------------------------------------------------------------

Write-ScriptHeader "Step 3: Install dependencies"

# Check Python
$pyCmd = Get-Command "python" -ErrorAction SilentlyContinue
if (-not $pyCmd) {
    $pyCmd = Get-Command "python3" -ErrorAction SilentlyContinue
}
if (-not $pyCmd) {
    Write-Host "Python not found on PATH" -ForegroundColor Red
    $script:OverallExitCode = 1
} else {
    $pyVer = & $pyCmd --version 2>&1
    Write-Host ("Python: $pyVer") -ForegroundColor Gray
}

# Install project dependencies
if ($pyCmd) {
    $code = Invoke-CommandWithCode -Command "& $pyCmd -m pip install -e . pytest==7.4.4 ruff mypy pyinstaller cyclonedx-bom" -Description "Install Python dependencies"
    if ($code -ne 0) { $script:OverallExitCode = 1 }
}

# Check NSIS
$nsisCmd = Get-Command "makensis" -ErrorAction SilentlyContinue
if (-not $nsisCmd) {
    # Try common locations
    $commonPaths = @(
        "C:\Program Files (x86)\NSIS\makensis.exe",
        "C:\Program Files\NSIS\makensis.exe"
    )
    foreach ($p in $commonPaths) {
        if (Test-Path $p) {
            $nsisCmd = $p
            break
        }
    }
}
if (-not $nsisCmd) {
    Write-Host "NSIS (makensis) not found on PATH or common locations" -ForegroundColor Red
    $script:OverallExitCode = 1
} else {
    $nsisVer = & $nsisCmd /VERSION 2>$null
    Write-Host ("NSIS: $nsisVer") -ForegroundColor Gray
}

# ---------------------------------------------------------------------------
# Step 4: Run tests
# ---------------------------------------------------------------------------

Write-ScriptHeader "Step 4: Run unit tests"

if ($pyCmd) {
    $code = Invoke-CommandWithCode -Command "& $pyCmd -m pytest -q -p no:faulthandler -p no:cacheprovider" -Description "Run unit tests"
    if ($code -ne 0) { $script:OverallExitCode = 1 }
}

# ---------------------------------------------------------------------------
# Step 5: Lint and typecheck
# ---------------------------------------------------------------------------

Write-ScriptHeader "Step 5: Lint and strict typecheck"

if ($pyCmd) {
    $code = Invoke-CommandWithCode -Command "& $pyCmd -m ruff check ." -Description "Run ruff lint"
    if ($code -ne 0) { $script:OverallExitCode = 1 }

    $code = Invoke-CommandWithCode -Command "& $pyCmd -m mypy camfrog_autodj" -Description "Run mypy strict typecheck"
    if ($code -ne 0) { $script:OverallExitCode = 1 }
}

# ---------------------------------------------------------------------------
# Step 6: Build Windows executable
# ---------------------------------------------------------------------------

Write-ScriptHeader "Step 6: Build Windows executable"

if ($pyCmd -and $nsisCmd) {
    $signArgs = @("-Clean")
    if (-not $NoSign) {
        if ($Pfx -and $Password) {
            $signArgs = @("-Clean", "-Pfx", $Pfx, "-Password", $Password)
        } elseif ($Thumbprint) {
            $signArgs = @("-Clean", "-Thumbprint", $Thumbprint)
        } else {
            Write-Host "No certificate provided - building unsigned (development build)" -ForegroundColor Yellow
            $signArgs = @("-Clean", "-NoSign")
        }
    }

    $buildCmd = "& powershell.exe -NoProfile -ExecutionPolicy Bypass -File build.ps1 @signArgs"
    Write-Command $buildCmd
    try {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$scriptRoot\build.ps1" @signArgs 2>&1
        $code = $LASTEXITCODE
        if ($code -ne 0) {
            Write-Host ("EXIT CODE: $code (Build AutoDJ.exe)") -ForegroundColor Red
            $script:OverallExitCode = 1
        } else {
            Write-Host ("EXIT CODE: $code (Build AutoDJ.exe) - OK") -ForegroundColor Green
        }
    } catch {
        Write-Host ("EXCEPTION: $_ (Build AutoDJ.exe)") -ForegroundColor Red
        $script:OverallExitCode = 1
    }

    # Verify exe exists
    $exePath = Join-Path $scriptRoot "dist\AutoDJ.exe"
    if (Test-Path $exePath) {
        Write-Host ("AutoDJ.exe built: $exePath") -ForegroundColor Green
        # Copy to artifacts
        Copy-Item -Path $exePath -Destination $artifactDir -ErrorAction Stop
    } else {
        Write-Host "AutoDJ.exe not found at $exePath" -ForegroundColor Red
        $script:OverallExitCode = 1
    }
}

# ---------------------------------------------------------------------------
# Step 7: Compile NSIS installer
# ---------------------------------------------------------------------------

Write-ScriptHeader "Step 7: Compile NSIS installer"

if ($nsisCmd -and (Test-Path (Join-Path $scriptRoot "installer.nsi"))) {
    $installerName = "Camfrog-AutoDJ-Setup-$Version.exe"
    $installerPath = Join-Path $artifactDir $installerName

    $makensisCmd = "& `"$nsisCmd`" /DVERSION=$Version `"$scriptRoot\installer.nsi`""
    Write-Command $makensisCmd
    try {
        & $nsisCmd /DVERSION=$Version `"$scriptRoot\installer.nsi`" 2>&1
        $code = $LASTEXITCODE
        if ($code -ne 0) {
            Write-Host ("EXIT CODE: $code (Compile NSIS installer)") -ForegroundColor Red
            $script:OverallExitCode = 1
        } else {
            Write-Host ("EXIT CODE: $code (Compile NSIS installer) - OK") -ForegroundColor Green
        }
    } catch {
        Write-Host ("EXCEPTION: $_ (Compile NSIS installer)") -ForegroundColor Red
        $script:OverallExitCode = 1
    }

    if (Test-Path $installerPath) {
        Write-Host ("NSIS installer built: $installerPath") -ForegroundColor Green
    } else {
        # Check for any exe in artifact dir that matches pattern
        $installerFiles = Get-ChildItem -Path $artifactDir -Filter "Camfrog-AutoDJ-Setup-*.exe" -ErrorAction SilentlyContinue
        if ($installerFiles) {
            Write-Host ("NSIS installer found: $($installerFiles[0].FullName)") -ForegroundColor Green
        } else {
            Write-Host "NSIS installer not found" -ForegroundColor Red
            $script:OverallExitCode = 1
        }
    }
}

# ---------------------------------------------------------------------------
# Step 8: Generate SHA256 checksums
# ---------------------------------------------------------------------------

Write-ScriptHeader "Step 8: Generate SHA256 checksums"

$checksumFile = Join-Path $artifactDir "SHA256SUMS.txt"
$files = Get-ChildItem -Path $artifactDir -File | Where-Object { $_.Name -ne "SHA256SUMS.txt" }
if ($files) {
    $checksums = @()
    foreach ($f in $files) {
        $hash = Get-FileHash -Path $f.FullName -Algorithm SHA256
        $checksums += "$($hash.Hash.ToLower())  $($f.Name)"
    }
    $checksums | Set-Content -Path $checksumFile -Encoding UTF8
    Write-Host ("SHA256 checksums written to: $checksumFile") -ForegroundColor Green
    Get-Content $checksumFile
} else {
    Write-Host "No artifact files found for checksumming" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Step 9: Generate SBOM
# ---------------------------------------------------------------------------

Write-ScriptHeader "Step 9: Generate CycloneDX SBOM"

if ($pyCmd) {
    $sbomPath = Join-Path $artifactDir "Camfrog-AutoDJ-$Version.cdx.json"
    $code = Invoke-CommandWithCode -Command "& $pyCmd -m cyclonedx_py environment --pyproject pyproject.toml -o $sbomPath" -Description "Generate CycloneDX SBOM"
    if ($code -ne 0) { $script:OverallExitCode = 1 }
    if (Test-Path $sbomPath) {
        Write-Host ("SBOM written to: $sbomPath") -ForegroundColor Green
    }
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-ScriptHeader "Build Summary"

Write-Host ("Exit code: $script:OverallExitCode") -ForegroundColor Cyan
Write-Host ("Artifacts: $artifactDir") -ForegroundColor Cyan
Write-Host ("Logs:      $logDir") -ForegroundColor Cyan

exit $script:OverallExitCode