<#
.SYNOPSIS
    Camfrog AutoDJ - Windows 11 Automated Installer
    Installs prerequisites, builds AutoDJ.exe, configures the bot, and creates shortcuts.

.DESCRIPTION
    This script automates the complete setup of Camfrog AutoDJ on Windows 11:
    1. Verifies Windows 11
    2. Installs/updates prerequisites:
       - Python 3.11+ (via winget or official installer)
       - mpv player (via winget)
       - yt-dlp (via winget or pip)
       - VB-Cable virtual audio driver (optional, with download link)
    3. Sets up the project (clones or uses existing directory)
    4. Installs Python dependencies
    5. Builds AutoDJ.exe with PyInstaller and signs it
    6. Creates config.toml from template
    7. Creates Start Menu and Desktop shortcuts
    8. Optionally configures auto-start
    9. Runs verification checks

.PARAMETER ProjectDir
    Directory where the project will be installed (default: $env:USERPROFILE\CamfrogAutoDJ)

.PARAMETER NoBuild
    Skip building AutoDJ.exe (use pre-built if available)

.PARAMETER NoShortcuts
    Skip creating Start Menu and Desktop shortcuts

.PARAMETER AutoStart
    Create a shortcut in the Startup folder for auto-launch on login

.PARAMETER PythonVersion
    Minimum Python version to install (default: "3.11")

.PARAMETER GitBranch
    Git branch to clone (default: "main")

.PARAMETER Detailed
    Show detailed output

.PARAMETER Force
    Force reinstallation even if already installed

.PARAMETER SkipVBCable
    Skip VB-Cable installation prompt

.EXAMPLE
    .\install.ps1
    # Full interactive install to default location

.EXAMPLE
    .\install.ps1 -ProjectDir "D:\AutoDJ" -AutoStart -Verbose
    # Custom directory with auto-start and verbose output

.EXAMPLE
    .\install.ps1 -NoBuild -Force
    # Skip build, force reinstall deps

.NOTES
    Requires: Windows 11, Administrator rights (for VB-Cable, winget)
    Run from PowerShell 5.1+ or PowerShell 7+
    NOTE: This version uses ASCII-only characters for PowerShell 5.1 compatibility
#>

param(
    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$ProjectDir = "$env:USERPROFILE\CamfrogAutoDJ",

    [switch]$NoBuild,

    [switch]$NoShortcuts,

    [switch]$AutoStart,

    [ValidateNotNullOrEmpty()]
    [string]$PythonVersion = "3.11",

    [ValidateNotNullOrEmpty()]
    [string]$GitBranch = "main",

    [switch]$Detailed,

    [switch]$Force,

    [switch]$SkipVBCable
)

# ============================================================================
# CONFIGURATION & GLOBALS
# ============================================================================
$ScriptDir = $PSScriptRoot
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$LOG_FILE = Join-Path $env:TEMP "autodj-install-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
$REPO_URL = "https://github.com/cvsz/autodj.git"
$VBCABLE_URL = "https://vb-audio.com/Cable/"
$VBCABLE_DOWNLOAD = "https://vb-audio.com/Cable/VB-CABLE_Driver_Pack43.zip"

# Colors
$C_CYAN = [ConsoleColor]::Cyan
$C_GREEN = [ConsoleColor]::Green
$C_YELLOW = [ConsoleColor]::Yellow
$C_RED = [ConsoleColor]::Red
$C_WHITE = [ConsoleColor]::White
$C_GRAY = [ConsoleColor]::Gray

# Add WinGet package directories to PATH for already-installed packages
$wingetPackages = @(
    "mpv-player.mpv-CI.MSVC*",
    "yt-dlp.yt-dlp*"
)
foreach ($pkgPattern in $wingetPackages) {
    $pkgDir = Get-ChildItem (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages\$pkgPattern") -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pkgDir -and ($env:PATH -notlike "*$($pkgDir.FullName)*")) {
        $env:PATH += ";" + $pkgDir.FullName
    }
}

# State tracking
$script:State = @{
    Windows11Verified = $false
    PythonInstalled = $false
    MpvInstalled = $false
    YtDlpInstalled = $false
    VBCableInstalled = $false
    ProjectCloned = $false
    DepsInstalled = $false
    ExeBuilt = $false
    ConfigCreated = $false
    ShortcutsCreated = $false
    AutoStartCreated = $false
    ChecksPassed = $false
}

# ============================================================================
# LOGGING & UI HELPERS
# ============================================================================
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp [$Level] $Message" | Out-File -FilePath $LOG_FILE -Append -Encoding utf8
    if (($Detailed) -or ($Level -in @("WARN", "ERROR", "FATAL"))) {
        Write-Host "[$Level] $Message"
    }
}

function Step {
    param([string]$Title)
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor $C_CYAN
    Write-Host "  $Title" -ForegroundColor $C_CYAN
    Write-Host "================================================================================" -ForegroundColor $C_CYAN
    Write-Log "STEP: $Title"
}

function SubStep {
    param([string]$Message, [switch]$Success, [switch]$Warning, [switch]$Error)
    $prefix = "  ->"
    $color = $C_WHITE
    if ($Success) { $prefix = "  [OK]"; $color = $C_GREEN }
    elseif ($Warning) { $prefix = "  [WARN]"; $color = $C_YELLOW }
    elseif ($Error) { $prefix = "  [FAIL]"; $color = $C_RED }
    Write-Host "$prefix $Message" -ForegroundColor $color
    $level = if ($Error) { "ERROR" } elseif ($Warning) { "WARN" } elseif ($Success) { "OK" } else { "INFO" }
    Write-Log "$Message" -Level $level
}

function Confirm {
    param([string]$Message, [switch]$DefaultYes = $true)
    $suffix = if ($DefaultYes) { "[Y/n]" } else { "[y/N]" }
    Write-Host "$Message $suffix"
    $response = Read-Host
    if ([string]::IsNullOrWhiteSpace($response)) { return $DefaultYes }
    return $response.Trim().ToLower().StartsWith("y")
}

function Check-Admin {
    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-WinVersion {
    $os = Get-CimInstance Win32_OperatingSystem
    return @{
        Caption = $os.Caption
        Version = $os.Version
        BuildNumber = $os.BuildNumber
    }
}

# ============================================================================
# PREREQUISITE CHECKS
# ============================================================================
function Check-Windows11 {
    Step "Checking Windows Version"
    $win = Get-WinVersion
    Write-Log "OS: $($win.Caption) $($win.Version) Build $($win.BuildNumber)"
    SubStep "Windows: $($win.Caption) (Build $($win.BuildNumber))"

    # Windows 11 is build 22000+
    if ($win.BuildNumber -ge 22000) {
        SubStep "Windows 11 detected (Build $($win.BuildNumber))" -Success
        $script:State.Windows11Verified = $true
        return $true
    }
    else {
        SubStep "Windows 11 REQUIRED (Build 22000+). Current: Build $($win.BuildNumber)" -Error
        Write-Log "FATAL: Windows 11 required" -Level "FATAL"
        return $false
    }
}

function Check-Command {
    param([string]$Name, [string]$Command, [string]$VersionArg = "--version")
    try {
        $result = & $Command $VersionArg 2>$null
        if (($LASTEXITCODE -eq 0) -and $result) {
            SubStep ("{0}: {1}" -f $Name, $result.Trim()) -Success
            return $true
        }
    }
    catch { }
    SubStep ("{0}: Not found" -f $Name) -Warning
    return $false
}

function Check-Python {
    Step "Checking Python"
    $found = $false
    foreach ($cmd in @("python", "python3", "py")) {
        if (Check-Command "Python ($cmd)" $cmd) {
            $version = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($version -and [version]$version -ge [version]$PythonVersion) {
                SubStep "Python $version meets requirement (>= $PythonVersion)" -Success
                $script:State.PythonInstalled = $true
                $script:PythonCmd = $cmd
                return $true
            }
            else {
                SubStep "Python $version is too old (need >= $PythonVersion)" -Warning
            }
        }
    }
    return $false
}

function Check-Mpv {
    Step "Checking mpv"
    if (Check-Command "mpv" "mpv") {
        $script:State.MpvInstalled = $true
        return $true
    }
    return $false
}

function Check-YtDlp {
    Step "Checking yt-dlp"
    if (Check-Command "yt-dlp" "yt-dlp") {
        $script:State.YtDlpInstalled = $true
        return $true
    }
    # Also check if yt-dlp.exe exists next to mpv
    $mpvPath = (Get-Command mpv -ErrorAction SilentlyContinue).Source
    if ($mpvPath) {
        $ytDlpNextToMpv = Join-Path (Split-Path $mpvPath) "yt-dlp.exe"
        if (Test-Path $ytDlpNextToMpv) {
            SubStep "yt-dlp found next to mpv: $ytDlpNextToMpv" -Success
            $script:State.YtDlpInstalled = $true
            return $true
        }
    }
    return $false
}

function Check-VBCable {
    Step "Checking VB-Cable Virtual Audio Driver"
    # Check for VB-Cable in audio devices
    try {
        $devices = Get-PnpDevice -Class "MEDIA" -ErrorAction SilentlyContinue |
            Where-Object { $_.FriendlyName -like "*VB-Cable*" -or $_.FriendlyName -like "*Virtual*" }
        if ($devices) {
            SubStep "VB-Cable detected: $($devices.FriendlyName -join ', ')" -Success
            $script:State.VBCableInstalled = $true
            return $true
        }
    }
    catch { }
    SubStep "VB-Cable not found (needed to route audio to Camfrog mic)" -Warning
    return $false
}

# ============================================================================
# INSTALLATION FUNCTIONS
# ============================================================================
function Install-WingetPackage {
    param([string]$Id, [string]$Name, [switch]$ForceInstall)
    SubStep "Installing $Name via winget..."
    Write-Log "Installing winget package: $Id"
    try {
        $args = "install", "--id", $Id, "--silent", "--accept-source-agreements", "--accept-package-agreements"
        if ($ForceInstall) { $args += "--force" }
        $proc = Start-Process "winget" -ArgumentList $args -Wait -PassThru -NoNewWindow
        # WinGet returns 0 on success, but also non-zero if already installed
        # Check if package is now available
        if ($proc.ExitCode -eq 0) {
            SubStep "$Name installed successfully" -Success
            return $true
        }
        else {
            # Check if package was already installed (common case)
            # Try to find the executable in WinGet package folder
            $pkgPattern = $Id -replace "\.", "*"
            $pkgDir = Get-ChildItem (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages\$pkgPattern*") -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($pkgDir) {
                $exe = Get-ChildItem $pkgDir.FullName -Recurse -Filter "*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
                if ($exe) {
                    $env:PATH += ";" + $pkgDir.FullName
                    SubStep "$Name already installed (added to PATH)" -Success
                    return $true
                }
            }
            SubStep "$Name installation failed (exit code: $($proc.ExitCode))" -Error
            return $false
        }
    }
    catch {
        SubStep "$Name installation error: $_" -Error
        return $false
    }
}

function Install-Python {
    Step "Installing Python $PythonVersion+"
    if ($script:State.PythonInstalled -and (-not $Force)) {
        SubStep "Python already installed, skipping" -Success
        return $true
    }

    # Try winget first
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        if (Install-WingetPackage "Python.Python.3.11" "Python 3.11" -ForceInstall:$Force) {
            # Refresh environment
            $env:PATH = [Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [Environment]::GetEnvironmentVariable("PATH", "User")
            return Check-Python
        }
    }

    # Fallback: download installer
    SubStep "winget not available or failed, downloading Python installer..." -Warning
    $url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    $installer = Join-Path $env:TEMP "python-3.11.9-amd64.exe"
    try {
        SubStep "Downloading Python installer..."
        Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
        SubStep "Running Python installer (quiet, install for all users)..."
        $args = "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_test=0"
        $proc = Start-Process $installer -ArgumentList $args -Wait -PassThru
        if ($proc.ExitCode -eq 0) {
            SubStep "Python installed successfully" -Success
            $env:PATH = [Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [Environment]::GetEnvironmentVariable("PATH", "User")
            return Check-Python
        }
        else {
            SubStep "Python installer failed (exit code: $($proc.ExitCode))" -Error
            return $false
        }
    }
    catch {
        SubStep "Python download/install failed: $_" -Error
        return $false
    }
}

function Install-Mpv {
    Step "Installing mpv"
    if ($script:State.MpvInstalled -and (-not $Force)) {
        SubStep "mpv already installed, skipping" -Success
        return $true
    }

    if (Get-Command winget -ErrorAction SilentlyContinue) {
        if (Install-WingetPackage "mpv-player.mpv-CI.MSVC" "mpv") {
            # WinGet installs to a package-specific folder, add it to PATH
            $wingetPkgDir = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages\mpv-player.mpv-CI.MSVC*"
            $pkgDir = Get-ChildItem $wingetPkgDir -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($pkgDir) {
                $env:PATH += ";" + $pkgDir.FullName
                SubStep "Added WinGet package dir to PATH: $($pkgDir.FullName)" -Success
            }
            # Also refresh from registry
            $env:PATH = [Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [Environment]::GetEnvironmentVariable("PATH", "User")
            return Check-Mpv
        }
    }

    # Fallback: chocolatey
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        SubStep "Trying Chocolatey..."
        choco install mpv -y --no-progress
        return Check-Mpv
    }

    # Manual download
    SubStep "No package manager found. Please install mpv manually from https://mpv.io/installation/" -Error
    SubStep "After installing, ensure mpv.exe is on PATH and yt-dlp.exe is in the same folder" -Warning
    return $false
}

function Install-YtDlp {
    Step "Installing yt-dlp"
    if ($script:State.YtDlpInstalled -and (-not $Force)) {
        SubStep "yt-dlp already available, skipping" -Success
        return $true
    }

    # Try winget
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        if (Install-WingetPackage "yt-dlp.yt-dlp" "yt-dlp") {
            # Refresh PATH after winget install
            $env:PATH = [Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [Environment]::GetEnvironmentVariable("PATH", "User")
            $script:State.YtDlpInstalled = $true
            return $true
        }
    }

    # Try pip (after Python is installed)
    if ($script:PythonCmd) {
        SubStep "Installing yt-dlp via pip..."
        & $script:PythonCmd -m pip install -U yt-dlp --quiet
        if ($LASTEXITCODE -eq 0) {
            SubStep "yt-dlp installed via pip" -Success
            $script:State.YtDlpInstalled = $true
            return $true
        }
    }

    # Manual download
    SubStep "Downloading yt-dlp.exe to mpv folder..." -Warning
    $mpvPath = (Get-Command mpv -ErrorAction SilentlyContinue).Source
    if ($mpvPath) {
        $mpvDir = Split-Path $mpvPath
        $ytDlpExe = Join-Path $mpvDir "yt-dlp.exe"
        try {
            Invoke-WebRequest -Uri "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" -OutFile $ytDlpExe -UseBasicParsing
            SubStep "yt-dlp.exe downloaded to $ytDlpExe" -Success
            $script:State.YtDlpInstalled = $true
            return $true
        }
        catch {
            SubStep "Failed to download yt-dlp.exe: $_" -Error
        }
    }
    else {
        SubStep "mpv not found, cannot determine where to place yt-dlp.exe" -Error
    }
    return $false
}

function Install-VBCable {
    if ($SkipVBCable) {
        SubStep "Skipping VB-Cable installation (--SkipVBCable)" -Warning
        return $true
    }

    Step "VB-Cable Virtual Audio Driver"
    if ($script:State.VBCableInstalled -and (-not $Force)) {
        SubStep "VB-Cable already installed, skipping" -Success
        return $true
    }

    if (-not (Check-Admin)) {
        SubStep "VB-Cable installation requires Administrator rights" -Warning
        SubStep "Please run this script as Administrator, or install manually from:" -Warning
        SubStep "  $VBCABLE_URL" -Warning
        return $false
    }

    if (Confirm "Download and install VB-Cable Driver Pack? (Required to route audio to Camfrog mic)") {
        $zipPath = Join-Path $env:TEMP "VB-CABLE_Driver_Pack43.zip"
        $extractPath = Join-Path $env:TEMP "VBCABLE"
        try {
            SubStep "Downloading VB-Cable Driver Pack..."
            Invoke-WebRequest -Uri $VBCABLE_DOWNLOAD -OutFile $zipPath -UseBasicParsing
            SubStep "Extracting..."
            Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force
            # Run installer (VBCABLE_Setup_x64.exe)
            $setup = Get-ChildItem $extractPath -Recurse -Filter "*Setup*x64*.exe" | Select-Object -First 1
            if ($setup) {
                SubStep "Running VB-Cable installer (silent)..."
                $proc = Start-Process $setup.FullName -ArgumentList "/S" -Wait -PassThru
                if ($proc.ExitCode -eq 0) {
                    SubStep "VB-Cable installed successfully" -Success
                    SubStep "IMPORTANT: Restart your PC for the driver to take effect!" -Warning
                    $script:State.VBCableInstalled = $true
                    return $true
                }
                else {
                    SubStep "VB-Cable installer exited with code $($proc.ExitCode)" -Error
                }
            }
            else {
                SubStep "Could not find VB-Cable x64 installer in extracted files" -Error
            }
        }
        catch {
            SubStep "VB-Cable installation failed: $_" -Error
        }
    }
    else {
        SubStep "VB-Cable installation skipped. You must install it manually later." -Warning
        SubStep "Download from: $VBCABLE_URL" -Warning
    }
    return $false
}

# ============================================================================
# PROJECT SETUP
# ============================================================================
function Setup-Project {
    Step "Setting up Camfrog AutoDJ Project"
    if (Test-Path $ProjectDir) {
        if ($Force -or (Confirm "Directory $ProjectDir exists. Overwrite?")) {
            SubStep "Removing existing directory..."
            Remove-Item -Recurse -Force $ProjectDir -ErrorAction SilentlyContinue
        }
        else {
            SubStep "Using existing project directory" -Warning
            $script:State.ProjectCloned = $true
            return $true
        }
    }

    SubStep "Cloning repository from $REPO_URL (branch: $GitBranch)..."
    try {
        git clone --branch $GitBranch --depth 1 $REPO_URL $ProjectDir
        if ($LASTEXITCODE -eq 0) {
            SubStep "Repository cloned to $ProjectDir" -Success
            $script:State.ProjectCloned = $true
            return $true
        }
        else {
            SubStep "Git clone failed" -Error
            return $false
        }
    }
    catch {
        SubStep "Git clone error: $_" -Error
        return $false
    }
}

function Install-PythonDeps {
    Step "Installing Python Dependencies"
    if (-not $script:State.ProjectCloned) { return $false }
    Set-Location $ProjectDir

    if ($script:State.DepsInstalled -and (-not $Force)) {
        SubStep "Dependencies already installed, skipping" -Success
        return $true
    }

    SubStep "Upgrading pip..."
    & $script:PythonCmd -m pip install --upgrade pip --quiet

    SubStep "Installing project in editable mode with build dependencies..."
    & $script:PythonCmd -m pip install -e ".[build,dev]" --quiet
    if ($LASTEXITCODE -eq 0) {
        SubStep "Python dependencies installed" -Success
        $script:State.DepsInstalled = $true
        return $true
    }
    else {
        SubStep "Failed to install Python dependencies" -Error
        return $false
    }
}

function Build-Exe {
    if ($NoBuild) {
        Step "Skipping Build (--NoBuild)"
        SubStep "Build skipped by user request" -Warning
        return $true
    }

    Step "Building AutoDJ.exe"
    if (-not $script:State.DepsInstalled) {
        SubStep "Dependencies not installed, cannot build" -Error
        return $false
    }
    Set-Location $ProjectDir

    # Check if build.ps1 exists
    if (-not (Test-Path "build.ps1")) {
        SubStep "build.ps1 not found in project directory" -Error
        return $false
    }

    SubStep "Running build.ps1 (this may take a minute)..."
    Write-Log "Starting build.ps1"
    try {
        # Run build.ps1 with -NoSign for faster builds (self-signed cert is optional)
        $buildArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "build.ps1")
        if ($Force) { $buildArgs += "-Clean" }
        $proc = Start-Process powershell.exe -ArgumentList $buildArgs -Wait -PassThru -NoNewWindow -WorkingDirectory $ProjectDir
        if ($proc.ExitCode -eq 0 -and (Test-Path "dist\AutoDJ.exe")) {
            SubStep "AutoDJ.exe built successfully at $ProjectDir\dist\AutoDJ.exe" -Success
            $script:State.ExeBuilt = $true
            return $true
        }
        else {
            SubStep "Build failed (exit code: $($proc.ExitCode))" -Error
            return $false
        }
    }
    catch {
        SubStep "Build error: $_" -Error
        return $false
    }
}

function Create-Config {
    Step "Creating Configuration"
    if (-not $script:State.ProjectCloned) { return $false }
    Set-Location $ProjectDir

    $configPath = "config.toml"
    $examplePath = "config.example.toml"

    if ((Test-Path $configPath) -and (-not $Force)) {
        SubStep "config.toml already exists, skipping" -Success
        $script:State.ConfigCreated = $true
        return $true
    }

    if (-not (Test-Path $examplePath)) {
        SubStep "config.example.toml not found" -Error
        return $false
    }

    SubStep "Copying config.example.toml to config.toml..."
    Copy-Item $examplePath $configPath -Force

    # Interactive config edits - simplified to avoid regex issues
    try {
        if (Confirm "Configure basic settings now? (bot nickname, admin, music folder)") {
            Write-Host "Bot nickname in Camfrog room [AutoDJ]:"
            $botNick = Read-Host
            if (-not $botNick) { $botNick = "AutoDJ" }
            Write-Host "Your Camfrog nickname (admin):"
            $adminNick = Read-Host
            Write-Host "Music folder path [D:\Music]:"
            $musicDir = Read-Host
            if (-not $musicDir) { $musicDir = "D:\Music" }

            $content = Get-Content $configPath -Raw
            # Use simple string replacement for the key values
            $content = $content -replace 'bot_nick = "AutoDJ"', ('bot_nick = "' + $botNick + '"')
            $content = $content -replace 'admins = \["Seaza"\]', ('admins = ["' + $adminNick + '"]')
            $musicDirFixed = $musicDir -replace '\\', '/'
            $content = $content -replace 'music_dirs = \["D:/Music"\]', ('music_dirs = ["' + $musicDirFixed + '"]')
            Set-Content $configPath -Value $content -Encoding utf8
            SubStep "Configuration updated with your settings" -Success
        }
        else {
            SubStep "Created config.toml from template. Edit it before running!" -Warning
        }
    }
    catch {
        SubStep "Config step failed: $_" -Error
        SubStep "Created config.toml from template. Edit it before running!" -Warning
    }

    $script:State.ConfigCreated = $true
    return $true
}

# ============================================================================
# SHORTCUTS & AUTO-START
# ============================================================================
function Create-Shortcuts {
    if ($NoShortcuts) {
        Step "Skipping Shortcuts (--NoShortcuts)"
        return $true
    }

    Step "Creating Shortcuts"
    if ((-not $script:State.ExeBuilt) -and (-not (Test-Path "$ProjectDir\dist\AutoDJ.exe"))) {
        SubStep "AutoDJ.exe not found, skipping shortcuts" -Warning
        return $false
    }

    $exePath = "$ProjectDir\dist\AutoDJ.exe"
    $iconPath = "$ProjectDir\app.ico"
    $wsh = New-Object -ComObject WScript.Shell

    # Desktop shortcut
    $desktop = [Environment]::GetFolderPath("Desktop")
    $desktopShortcut = Join-Path $desktop "Camfrog AutoDJ.lnk"
    $shortcut = $wsh.CreateShortcut($desktopShortcut)
    $shortcut.TargetPath = $exePath
    $shortcut.Arguments = "--gui"
    $shortcut.WorkingDirectory = "$ProjectDir\dist"
    $shortcut.IconLocation = $iconPath
    $shortcut.Description = "Camfrog AutoDJ - Music bot for Camfrog rooms"
    $shortcut.Save()
    SubStep "Desktop shortcut created" -Success

    # Start Menu shortcut
    $startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
    $autoDjFolder = Join-Path $startMenu "Camfrog AutoDJ"
    if (-not (Test-Path $autoDjFolder)) { New-Item -ItemType Directory -Path $autoDjFolder | Out-Null }
    $startShortcut = Join-Path $autoDjFolder "Camfrog AutoDJ.lnk"
    $shortcut = $wsh.CreateShortcut($startShortcut)
    $shortcut.TargetPath = $exePath
    $shortcut.Arguments = "--gui"
    $shortcut.WorkingDirectory = "$ProjectDir\dist"
    $shortcut.IconLocation = $iconPath
    $shortcut.Description = "Camfrog AutoDJ - Music bot for Camfrog rooms"
    $shortcut.Save()
    SubStep "Start Menu shortcut created" -Success

    # Config shortcut
    $configShortcut = Join-Path $autoDjFolder "Edit Config.lnk"
    $shortcut = $wsh.CreateShortcut($configShortcut)
    $shortcut.TargetPath = "notepad.exe"
    $shortcut.Arguments = "$ProjectDir\config.toml"
    $shortcut.WorkingDirectory = $ProjectDir
    $shortcut.Description = "Edit AutoDJ configuration"
    $shortcut.Save()
    SubStep "Config editor shortcut created" -Success

    # Uninstall shortcut
    $uninstallShortcut = Join-Path $autoDjFolder "Uninstall.lnk"
    $shortcut = $wsh.CreateShortcut($uninstallShortcut)
    $shortcut.TargetPath = "powershell.exe"
    $shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$ProjectDir\uninstall.ps1`""
    $shortcut.WorkingDirectory = $ProjectDir
    $shortcut.Description = "Uninstall Camfrog AutoDJ"
    $shortcut.Save()
    SubStep "Uninstall shortcut created" -Success

    $script:State.ShortcutsCreated = $true
    return $true
}

function Create-AutoStart {
    if (-not $AutoStart) { return $true }

    Step "Configuring Auto-Start"
    if ((-not $script:State.ExeBuilt) -and (-not (Test-Path "$ProjectDir\dist\AutoDJ.exe"))) {
        SubStep "AutoDJ.exe not found, skipping auto-start" -Warning
        return $false
    }

    $startup = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
    $autoStartShortcut = Join-Path $startup "Camfrog AutoDJ.lnk"
    $exePath = "$ProjectDir\dist\AutoDJ.exe"
    $wsh = New-Object -ComObject WScript.Shell
    $shortcut = $wsh.CreateShortcut($autoStartShortcut)
    $shortcut.TargetPath = $exePath
    $shortcut.Arguments = "--gui"
    $shortcut.WorkingDirectory = "$ProjectDir\dist"
    $shortcut.IconLocation = "$ProjectDir\app.ico"
    $shortcut.Description = "Camfrog AutoDJ - Auto-start on login"
    $shortcut.Save()
    SubStep "Auto-start shortcut created in Startup folder" -Success
    $script:State.AutoStartCreated = $true
    return $true
}

# ============================================================================
# VERIFICATION
# ============================================================================
function Run-Verification {
    Step "Running Verification Checks"
    if ((-not $script:State.ExeBuilt) -and (-not (Test-Path "$ProjectDir\dist\AutoDJ.exe"))) {
        SubStep "AutoDJ.exe not found, skipping verification" -Warning
        return $false
    }

    Set-Location "$ProjectDir\dist"
    $exe = ".\AutoDJ.exe"

    SubStep "Running AutoDJ.exe --check..."
    try {
        # Use temp files to capture output (must be different files for stdout/stderr)
        $tempOut = [System.IO.Path]::GetTempFileName()
        $tempErr = [System.IO.Path]::GetTempFileName()
        $proc = Start-Process $exe -ArgumentList "--check" -Wait -PassThru -NoNewWindow -RedirectStandardOutput $tempOut -RedirectStandardError $tempErr
        $exitCode = $proc.ExitCode
        $result = Get-Content $tempOut
        $errors = Get-Content $tempErr
        Remove-Item $tempOut, $tempErr -Force -ErrorAction SilentlyContinue

        # Combine stdout and stderr
        $allOutput = $result + $errors

        foreach ($line in $allOutput) {
            # Match various formats: [OK], [ OK ], [WARN], [FAIL], [INFO], or timestamped lines
            if ($line -match "^\[ ?(OK|INFO|WARN|FAIL) ?\]") {
                $level = $matches[1]
                $msg = $line -replace "^\[ ?(OK|INFO|WARN|FAIL) ?\]\s*", ""
                switch ($level) {
                    "OK" { SubStep $msg -Success }
                    "INFO" { SubStep $msg }
                    "WARN" { SubStep $msg -Warning }
                    "FAIL" { SubStep $msg -Error }
                }
            }
            elseif ($line -match "^\[\d{4}-\d{2}-\d{2}") {
                # Timestamped log line - show as info
                Write-Host "  $line" -ForegroundColor $C_GRAY
            }
            else {
                Write-Host "  $line" -ForegroundColor $C_GRAY
            }
        }

        if ($exitCode -eq 0) {
            SubStep "All checks passed!" -Success
            $script:State.ChecksPassed = $true
            return $true
        }
        else {
            SubStep "Some checks failed (see above). Run 'AutoDJ.exe --check -v' for details." -Warning
            return $false
        }
    }
    catch {
        Write-Log "Run-Verification error: $_" -Level "ERROR"
        SubStep "Verification error: $_" -Error
        return $false
    }
}

# ============================================================================
# UNINSTALLER GENERATION
# ============================================================================
function Create-Uninstaller {
    $uninstallPath = Join-Path $ProjectDir "uninstall.ps1"
    $content = @"
<#
.SYNOPSIS
    Camfrog AutoDJ Uninstaller
#>
param([switch]`$Force)

`$ProjectDir = "$ProjectDir"
`$ErrorActionPreference = "Continue"

Write-Host "Uninstalling Camfrog AutoDJ..." -ForegroundColor Cyan

# Remove shortcuts
`$startMenu = Join-Path `$env:APPDATA "Microsoft\Windows\Start Menu\Programs"
`$autoDjFolder = Join-Path `$startMenu "Camfrog AutoDJ"
if (Test-Path `$autoDjFolder) { Remove-Item -Recurse -Force `$autoDjFolder; "Removed Start Menu folder" }

`$desktop = [Environment]::GetFolderPath("Desktop")
`$desktopShortcut = Join-Path `$desktop "Camfrog AutoDJ.lnk"
if (Test-Path `$desktopShortcut) { Remove-Item -Force `$desktopShortcut; "Removed Desktop shortcut" }

`$startup = Join-Path `$env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
`$autoStartShortcut = Join-Path `$startup "Camfrog AutoDJ.lnk"
if (Test-Path `$autoStartShortcut) { Remove-Item -Force `$autoStartShortcut; "Removed auto-start shortcut" }

# Remove project directory
if (`$Force -or (Read-Host "Remove project directory `$ProjectDir? [y/N]" -eq "y")) {
    if (Test-Path `$ProjectDir) { Remove-Item -Recurse -Force `$ProjectDir; "Removed `$ProjectDir" }
}

Write-Host "Uninstall complete." -ForegroundColor Green
Read-Host "Press Enter to exit"
"@
    Set-Content $uninstallPath -Value $content -Encoding utf8
    SubStep "Uninstaller created at $uninstallPath" -Success
}

# ============================================================================
# MAIN
# ============================================================================
function Main {
    # Header
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor $C_CYAN
    Write-Host "           Camfrog AutoDJ - Windows 11 Automated Installer" -ForegroundColor $C_CYAN
    Write-Host "                         Version 0.2.5" -ForegroundColor $C_CYAN
    Write-Host "================================================================================" -ForegroundColor $C_CYAN
    Write-Host ""
    Write-Log "=== Camfrog AutoDJ Installer Started ==="
    Write-Log "ProjectDir: $ProjectDir"
    Write-Log "NoBuild: $NoBuild, NoShortcuts: $NoShortcuts, AutoStart: $AutoStart"
    Write-Log "Detailed: $Detailed, Force: $Force, SkipVBCable: $SkipVBCable"

    # Check admin early
    $isAdmin = Check-Admin
    if ($isAdmin) { SubStep "Running as Administrator" -Success }
    else { SubStep "Not running as Administrator (VB-Cable install will be skipped)" -Warning }

    # Step 1: Windows 11 check
    if (-not (Check-Windows11)) { return 1 }

    # Step 2: Prerequisites
    Check-Python | Out-Null
    Check-Mpv | Out-Null
    Check-YtDlp | Out-Null
    Check-VBCable | Out-Null

    # Install missing prerequisites
    if (-not $script:State.PythonInstalled) { Install-Python | Out-Null }
    if (-not $script:State.MpvInstalled) { Install-Mpv | Out-Null }
    if (-not $script:State.YtDlpInstalled) { Install-YtDlp | Out-Null }
    if (-not $script:State.VBCableInstalled) { Install-VBCable | Out-Null }

    # Step 3: Project setup
    Setup-Project | Out-Null
    if (-not $script:State.ProjectCloned) { return 1 }

    # Step 4: Python dependencies
    Install-PythonDeps | Out-Null
    if (-not $script:State.DepsInstalled) { return 1 }

    # Step 5: Build
    Build-Exe | Out-Null

    # Step 6: Config
    try {
        Create-Config | Out-Null
    }
    catch {
        Write-Log "Create-Config failed: $_" -Level "ERROR"
        SubStep "Config step failed: $_" -Error
    }

    # Step 6b: Copy config.toml to dist for verification
    if (Test-Path "$ProjectDir\config.toml") {
        if (-not (Test-Path "$ProjectDir\dist")) {
            New-Item -ItemType Directory -Path "$ProjectDir\dist" | Out-Null
        }
        Copy-Item "$ProjectDir\config.toml" "$ProjectDir\dist\config.toml" -Force
        SubStep "Copied config.toml to dist" -Success
    }

    # Step 6c: Fix config.toml in dist with correct mpv/yt-dlp paths from WinGet
    try {
        $distConfig = "$ProjectDir\dist\config.toml"
        if (Test-Path $distConfig) {
            $content = Get-Content $distConfig -Raw
            
            # Find mpv in WinGet packages
            $mpvPkgDir = Get-ChildItem (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages\mpv-player.mpv-CI.MSVC*") -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($mpvPkgDir) {
                $mpvExe = Get-ChildItem $mpvPkgDir.FullName -Recurse -Filter "mpv.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
                if ($mpvExe) {
                    $mpvPath = $mpvExe.FullName -replace '\\', '/'
                    $content = $content -replace 'mpv_path = "C:/mpv/mpv.exe"', ("mpv_path = `"$mpvPath`"")
                }
            }
            
            # Find yt-dlp in WinGet links
            $ytDlpLink = "$env:LOCALAPPDATA\Microsoft\WinGet\Links\yt-dlp.EXE"
            if (Test-Path $ytDlpLink) {
                $ytDlpPath = $ytDlpLink -replace '\\', '/'
                $content = $content -replace 'ytdlp_path = ""', ("ytdlp_path = `"$ytDlpPath`"")
            }
            
            Set-Content $distConfig -Value $content -Encoding utf8
            SubStep "Fixed config.toml paths in dist" -Success
        }
    }
    catch {
        Write-Log "Fix config paths failed: $_" -Level "WARN"
    }

    # Step 7: Shortcuts
    try {
        Create-Shortcuts | Out-Null
    }
    catch {
        Write-Log "Create-Shortcuts failed: $_" -Level "ERROR"
        SubStep "Shortcuts step failed: $_" -Error
    }
    try {
        Create-AutoStart | Out-Null
    }
    catch {
        Write-Log "Create-AutoStart failed: $_" -Level "ERROR"
        SubStep "AutoStart step failed: $_" -Error
    }

    # Step 8: Uninstaller
    try {
        Create-Uninstaller
    }
    catch {
        Write-Log "Create-Uninstaller failed: $_" -Level "ERROR"
        SubStep "Uninstaller step failed: $_" -Error
    }

    # Step 9: Verification
    try {
        Run-Verification | Out-Null
    }
    catch {
        Write-Log "Run-Verification failed: $_" -Level "ERROR"
        SubStep "Verification step failed: $_" -Error
    }

    # Summary
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor $C_CYAN
    Write-Host "  INSTALLATION SUMMARY" -ForegroundColor $C_CYAN
    Write-Host "================================================================================" -ForegroundColor $C_CYAN

    $summary = @(
        @{ Name = "Windows 11"; Status = $script:State.Windows11Verified },
        @{ Name = "Python $PythonVersion+"; Status = $script:State.PythonInstalled },
        @{ Name = "mpv"; Status = $script:State.MpvInstalled },
        @{ Name = "yt-dlp"; Status = $script:State.YtDlpInstalled },
        @{ Name = "VB-Cable"; Status = $script:State.VBCableInstalled },
        @{ Name = "Project cloned"; Status = $script:State.ProjectCloned },
        @{ Name = "Python deps"; Status = $script:State.DepsInstalled },
        @{ Name = "AutoDJ.exe built"; Status = $script:State.ExeBuilt },
        @{ Name = "Config created"; Status = $script:State.ConfigCreated },
        @{ Name = "Shortcuts"; Status = $script:State.ShortcutsCreated },
        @{ Name = "Auto-start"; Status = $script:State.AutoStartCreated },
        @{ Name = "Verification"; Status = $script:State.ChecksPassed }
    )

    foreach ($item in $summary) {
        $status = if ($item.Status) { "[OK]" } else { "[FAIL]" }
        $color = if ($item.Status) { $C_GREEN } else { $C_RED }
        Write-Host "  $status $($item.Name)" -ForegroundColor $color
    }

    Write-Host ""
    Write-Host "Install log: $LOG_FILE" -ForegroundColor $C_GRAY
    Write-Host ""

    if ($script:State.ExeBuilt -and $script:State.ConfigCreated) {
        Write-Host "[OK] Installation completed successfully!" -ForegroundColor $C_GREEN
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor $C_CYAN
        Write-Host "  1. Edit config.toml if you haven't: notepad $ProjectDir\config.toml" -ForegroundColor $C_WHITE
        Write-Host "  2. Open Camfrog and join your room" -ForegroundColor $C_WHITE
        Write-Host "  3. Run AutoDJ from Desktop/Start Menu or:" -ForegroundColor $C_WHITE
        Write-Host "     cd $ProjectDir\dist" -ForegroundColor $C_GRAY
        Write-Host "     .\AutoDJ.exe --gui" -ForegroundColor $C_GRAY
        Write-Host "  4. Run .\AutoDJ.exe --check to verify everything works" -ForegroundColor $C_WHITE
        Write-Host ""
        if (-not $script:State.VBCableInstalled) {
            Write-Host "[WARN] VB-Cable not installed - you MUST install it for audio to work in Camfrog!" -ForegroundColor $C_YELLOW
            Write-Host "   Download from: $VBCABLE_URL" -ForegroundColor $C_GRAY
            Write-Host "   After installing, set audio_device in config.toml (run: mpv --audio-device=help)" -ForegroundColor $C_GRAY
        }
        return 0
    }
    else {
        Write-Host "[FAIL] Installation completed with errors. Check the log: $LOG_FILE" -ForegroundColor $C_RED
        return 1
    }
}

# Run main
try {
    $exitCode = Main
    exit $exitCode
}
catch {
    Write-Host ""
    Write-Host "FATAL ERROR: $_" -ForegroundColor $C_RED
    Write-Log "FATAL: $_" -Level "FATAL"
    Write-Host "Install log: $LOG_FILE" -ForegroundColor $C_GRAY
    exit 1
}