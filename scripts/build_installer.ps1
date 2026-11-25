<#
.SYNOPSIS
    Build NSIS installer for AutoDJ
.DESCRIPTION
    This script builds the NSIS installer from the built artifacts in dist/
    Run from PowerShell on Windows (or via wine on Linux)
.NOTES
    Requires: NSIS 3.08+ (makensis.exe in PATH)
    Usage: powershell -ExecutionPolicy Bypass -File scripts/build_installer.ps1
#>

param(
    [string]$Version = "",
    [string]$SrcDir = "dist",
    [string]$OutDir = "dist",
    [switch]$Sign,
    # Full installer: the whole mpv folder (mpv.exe, yt-dlp.exe, _internal\, vbcable\, ...)
    # is mirrored into $SrcDir\mpv and installed by default. -NoMpv builds without it;
    # -RequireMpv fails the build when there is no bundle to package.
    [string]$MpvDir = "mpv",
    [switch]$NoMpv,
    [switch]$RequireMpv
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

# Everything below uses repo-root-relative paths (installer.nsi, dist\...), so anchor there.
Set-Location (Split-Path $PSScriptRoot -Parent)

# Default the version from pyproject.toml (never a stale hard-coded literal).
if (-not $Version) {
    $pyVersion = & python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
    $pyExit = $LASTEXITCODE
    $Version = "$pyVersion".Trim()
    if ($pyExit -ne 0 -or -not $Version) {
        throw "Could not read the version from pyproject.toml; pass -Version explicitly."
    }
}

Write-Host "=== AutoDJ Installer Builder ===" -ForegroundColor Cyan
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

# Stage the shipped config template and docs from the repo on every build, so the
# installer always carries the current config.example.toml (installer.nsi packages
# dist\config.toml) even when AutoDJ.exe was built earlier.  Never a developer's
# local config.toml: it may hold an API key and site-specific admins.
New-Item -ItemType Directory -Force -Path $SrcDir | Out-Null
$staged = @{
    "config.example.toml" = "config.toml"
    "README.md"           = "README.md"
    "CHANGELOG.md"        = "CHANGELOG.md"
    "LICENSE"             = "LICENSE"
    # installer.nsi packages dist\readme.txt (the Makefile's portable target copies it too)
    "dist-readme.txt"     = "readme.txt"
}
foreach ($src in $staged.Keys) {
    if (-not (Test-Path $src -PathType Leaf)) {
        throw "Required installer source file missing: $src"
    }
    Copy-Item $src (Join-Path $SrcDir $staged[$src]) -Force
    Write-Host "  Staged: $src -> $SrcDir\$($staged[$src])"
}

# installer.nsi packages dist\start.bat and dist\check.bat.  Only `make portable`
# created them, so a CI / release build (build.ps1 + this script) aborted with
# 'File: "dist\start.bat" -> no files found'.  Generate them here, from the same tool.
if (Test-Path (Join-Path $SrcDir "AutoDJ.exe") -PathType Leaf) {
    & python tools\make_client_shortcuts.py $SrcDir
    if ($LASTEXITCODE -ne 0) {
        throw "tools\make_client_shortcuts.py failed (exit $LASTEXITCODE)"
    }
}

# Bundle the complete mpv folder.  robocopy /MIR makes $SrcDir\mpv an exact copy (files
# removed from mpv\ disappear from the installer too). robocopy treats files with the same
# size and timestamps as unchanged without reading them, so every file is then compared
# by relative path, size and SHA-256: the installer never ships a partial or stale bundle.
function Get-TreeListing([string]$Root) {
    $base = (Resolve-Path $Root).Path.TrimEnd('\')
    Get-ChildItem -LiteralPath $base -Recurse -File | Sort-Object FullName |
        ForEach-Object {
            "{0}|{1}|{2}" -f $_.FullName.Substring($base.Length + 1), $_.Length,
                (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
        }
}
$mpvDest = Join-Path $SrcDir "mpv"
$bundleMpv = $false
if ($NoMpv) {
    Write-Host "mpv bundle: skipped (-NoMpv)"
} elseif (Test-Path (Join-Path $MpvDir "mpv.exe") -PathType Leaf) {
    robocopy $MpvDir $mpvDest /MIR /R:1 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
    $rc = $LASTEXITCODE
    $global:LASTEXITCODE = 0
    if ($rc -ge 8) { throw "mirroring $MpvDir -> $mpvDest failed (robocopy exit $rc): close any mpv/AutoDJ running from $mpvDest and retry" }
    # robocopy skips a file whose size and timestamps match even when its content differs
    # (it reports it as "same" or, on newer Windows, "modified"), and /IM does not exist on
    # older Windows. Re-copy every file whose hash differs, then verify again.
    $stale = @(Compare-Object @(Get-TreeListing $MpvDir) @(Get-TreeListing $mpvDest) |
        Where-Object SideIndicator -eq '<=' | ForEach-Object { ($_.InputObject -split '\|')[0] })
    foreach ($rel in $stale) {
        Copy-Item -LiteralPath (Join-Path $MpvDir $rel) -Destination (Join-Path $mpvDest $rel) -Force
    }
    if ($stale.Count) { Write-Host "mpv bundle: re-copied $($stale.Count) file(s) whose content differed from $MpvDir" }
    $diff = Compare-Object @(Get-TreeListing $MpvDir) @(Get-TreeListing $mpvDest)
    if ($diff) { throw "$mpvDest is not an exact copy of $MpvDir after mirroring: $($diff | Select-Object -First 5 | Out-String)" }
    $files = Get-ChildItem -LiteralPath $mpvDest -Recurse -File
    Write-Host ("mpv bundle: {0} files, {1:N1} MB mirrored from {2}" -f $files.Count, (($files | Measure-Object Length -Sum).Sum / 1MB), $MpvDir)
}
if (-not $NoMpv -and (Test-Path (Join-Path $mpvDest "mpv.exe") -PathType Leaf) -and (Test-Path (Join-Path $mpvDest "yt-dlp.exe") -PathType Leaf)) {
    $bundleMpv = $true
}
if ($RequireMpv -and -not $bundleMpv) {
    throw "-RequireMpv: no complete mpv bundle (mpv.exe + yt-dlp.exe) in $MpvDir or $mpvDest"
}
Write-Host ("Installer type: {0}" -f $(if ($bundleMpv) { "full (mpv bundle installed by default)" } else { "without mpv bundle" }))

# Verify source files exist
$requiredFiles = @(
    "AutoDJ.exe",
    "app.ico",
    "config.toml",
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
$optionalDirs = @("autodj", "docs", "tools", "tests")
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
if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }
# Call operator (not Start-Process -ArgumentList): Start-Process does not quote arguments,
# so a rendered-script path containing spaces would be split. /DOUTDIR makes installer.nsi
# write the installer into $OutDir (it used to land in the repo root, where `make` and
# build-all-hybrid.ps1 -- which look in dist\ -- could not find it).
$nsisArgs = @("-NOCD", "/DAPP_VERSION=$Version", "/DSRCDIR=.", "/DOUTDIR=$OutDir")
if ($bundleMpv) { $nsisArgs += "/DBUNDLE_MPV" }
if ($NoMpv) { $nsisArgs += "/DNO_MPV" }  # leave any staged dist\mpv out entirely
& $makensis @nsisArgs $renderedNsi
if ($LASTEXITCODE -ne 0) {
    Write-Error "NSIS build failed with exit code $LASTEXITCODE"
    exit 1
}

$installerPath = Join-Path (Resolve-Path $OutDir).Path $installerName
if (Test-Path $installerPath) {
    $sizeMB = [math]::Round((Get-Item $installerPath).Length / 1MB, 1)
    Write-Host "Installer built successfully!" -ForegroundColor Green
    Write-Host "  File: $installerPath"
    Write-Host "  Size: $sizeMB MB"

    # Sign if requested
    if ($Sign) {
        Write-Host "Signing installer..."
        # Only a valid, unexpired code-signing cert with a private key; newest first.
        $cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object {
            $_.HasPrivateKey -and $_.NotAfter -gt (Get-Date) -and $_.Subject -like "*ZEAZDEV*" -and
            ($_.EnhancedKeyUsageList | Where-Object { $_.ObjectId -eq "1.3.6.1.5.5.7.3.3" })
        } | Sort-Object NotAfter -Descending | Select-Object -First 1
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

