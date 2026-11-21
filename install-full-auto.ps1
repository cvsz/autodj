<#
.SYNOPSIS
    AutoDJ - Fully Automated One-Click Installer
    Installs ALL dependencies, configures EVERYTHING, ready to run.

.DESCRIPTION
    This is the ULTIMATE installer - run once, everything works:
    1. Installs Python, mpv, yt-dlp, Git, NSIS via winget
    2. Downloads & installs VB-Cable (prompts for reboot)
    3. Clones repo, builds AutoDJ.exe with self-signing
    4. Auto-discovers Camfrog window & chat controls
    5. Detects VB-Cable audio device & configures it
    6. Sets up ytsearch autoplay sources (no playlist URL needed)
    7. Creates Desktop/Start Menu shortcuts + auto-start
    8. Runs verification & launches GUI

.NOTES
    Run ONCE as Administrator. Reboots once for VB-Cable.
    After reboot, run again to complete setup.
#>

param(
    [switch]$SkipVBCable,           # Skip VB-Cable (install manually later)
    [switch]$NoAutoStart,           # Don't create startup shortcut
    [switch]$NoShortcuts,           # Don't create Desktop/Start Menu shortcuts
    [switch]$NoBuild,               # Use existing AutoDJ.exe if present
    [switch]$Unattended,            # No prompts, use all defaults
    [string]$ProjectDir = "$env:USERPROFILE\AutoDJ",
    [string]$PlaylistQuery = "cantonese r&b remix,mandopop 2024,chinese chill songs,廣東歌 remix"
)

# ============================================================================
# CONFIGURATION & GLOBALS
# ============================================================================
$ScriptDir = $PSScriptRoot
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$LOG_FILE = Join-Path $env:TEMP "autodj-full-install-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
$REPO_URL = "https://github.com/cvsz/autodj.git"
$VBCABLE_URL = "https://vb-audio.com/Cable/"
$VBCABLE_DOWNLOAD = "https://vb-audio.com/Cable/VB-CABLE_Driver_Pack43.zip"
# Note: vb-audio.com often changes URLs. If 404, manually download from https://vb-audio.com/Cable/

# Colors
$C_CYAN = [ConsoleColor]::Cyan
$C_GREEN = [ConsoleColor]::Green
$C_YELLOW = [ConsoleColor]::Yellow
$C_RED = [ConsoleColor]::Red
$C_WHITE = [ConsoleColor]::White
$C_GRAY = [ConsoleColor]::Gray

# State
$script:State = @{
    RebootRequired = $false
    VBCableInstalled = $false
    AudioDeviceConfigured = $false
    ConfigComplete = $false
}

# ============================================================================
# HELPERS
# ============================================================================
function Write-Log { param([string]$M,[string]$L="INFO"); "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [$L] $M" | Out-File -FilePath $LOG_FILE -Append -Encoding utf8; if ($L -in @("WARN","ERROR","FATAL")) { Write-Host "[$L] $M" } }
function Step { param([string]$T); Write-Host ""; Write-Host ("="*72) -Fore $C_CYAN; Write-Host "  $T" -Fore $C_CYAN; Write-Host ("="*72) -Fore $C_CYAN; Write-Log "STEP: $T" }
function Ok { param([string]$M); Write-Host "  [OK] $M" -Fore $C_GREEN; Write-Log $M "OK" }
function Warn { param([string]$M); Write-Host "  [WARN] $M" -Fore $C_YELLOW; Write-Log $M "WARN" }
function Fail { param([string]$M); Write-Host "  [FAIL] $M" -Fore $C_RED; Write-Log $M "ERROR" }
function Ask { param([string]$M,[switch]$D=$true); if($Unattended){return $D}; $s=if($D){"[Y/n]"}{"[y/N]"}; $r=Read-Host "$M $s"; if(!($r)){return $D}; return $r.Trim().ToLower().StartsWith("y") }
function IsAdmin { (New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator) }

# ============================================================================
# 1. VB-CABLE (with auto-reboot handling)
# ============================================================================
function Install-VBCableAuto {
    if ($SkipVBCable) { Warn "Skipping VB-Cable (manual install required later)"; return $true }
    Step "VB-Cable Virtual Audio Driver"
    if ($script:State.VBCableInstalled) { Ok "Already installed"; return $true }

    # Check if already installed
    $vb = Get-PnpDevice -Class MEDIA -ErrorAction SilentlyContinue | Where { $_.FriendlyName -like "*VB-Cable*" }
    if ($vb) { Ok "VB-Cable detected: $($vb.FriendlyName)"; $script:State.VBCableInstalled = $true; return $true }

    if (-not (IsAdmin)) { Fail "VB-Cable requires Admin. Re-run as Administrator."; return $false }
    if (-not (Ask "Download & install VB-Cable Driver Pack? (Required for Camfrog audio)")) { Warn "Skipped. You MUST install manually later from $VBCABLE_URL"; return $true }

    $zip = Join-Path $env:TEMP "VBCABLE.zip"
    $ext = Join-Path $env:TEMP "VBCABLE"
    try {
        Ok "Downloading VB-Cable..."
        Invoke-WebRequest -Uri $VBCABLE_DOWNLOAD -OutFile $zip -UseBasicParsing
        Ok "Extracting..."
        Expand-Archive -Path $zip -DestinationPath $ext -Force
        $setup = Get-ChildItem $ext -Recurse -Filter "*Setup*x64*.exe" | Select -First 1
        if (-not $setup) { Fail "VB-Cable x64 installer not found in extracted files"; return $false }
        Ok "Installing VB-Cable (silent)..."
        $proc = Start-Process $setup.FullName -ArgumentList "/S" -Wait -PassThru
        if ($proc.ExitCode -ne 0) { Fail "VB-Cable installer exited with code $($proc.ExitCode)"; return $false }
        Ok "VB-Cable installed! REBOOT REQUIRED."
        $script:State.RebootRequired = $true
        $script:State.VBCableInstalled = $true
        return $true
    } catch { Fail "VB-Cable install failed: $_"; return $false }
}

# ============================================================================
# 2. DEPENDENCIES via winget
# ============================================================================
function Install-DepsAuto {
    Step "Installing Dependencies (winget)"
    # Check each dependency
    $checks = @(
        @{Name="Python 3.11"; Cmd="python"; Id="Python.Python.3.11"},
        @{Name="mpv"; Cmd="mpv"; Id="mpv-player.mpv-CI.MSVC"},
        @{Name="yt-dlp"; Cmd="yt-dlp"; Id="yt-dlp.yt-dlp"},
        @{Name="Git"; Cmd="git"; Id="Git.Git"},
        @{Name="NSIS"; Cmd="makensis"; Id="NSIS.NSIS"}
    )

    foreach ($d in $checks) {
        $cmd = Get-Command $d.Cmd -ErrorAction SilentlyContinue
        if ($cmd) { Ok "$($d.Name) already installed"; continue }

        Ok "Installing $($d.Name)..."
        $proc = Start-Process winget -ArgumentList "install --id $($d.Id) --silent --accept-source-agreements --accept-package-agreements" -Wait -PassThru -NoNewWindow
        if ($proc.ExitCode -ne 0) { Warn "$($d.Name) install failed (may already exist). Continuing..." } else { Ok "$($d.Name) installed" }
    }
    # Refresh PATH from registry + WinGet package dirs
    $env:PATH = [Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [Environment]::GetEnvironmentVariable("PATH","User")
    $wingetPkgs = @("mpv-player.mpv-CI.MSVC*", "yt-dlp.yt-dlp*")
    foreach ($pkg in $wingetPkgs) {
        $pkgDir = Get-ChildItem (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages\$pkg") -Directory -ErrorAction SilentlyContinue | Select -First 1
        if ($pkgDir -and ($env:PATH -notlike "*$($pkgDir.FullName)*")) { $env:PATH += ";" + $pkgDir.FullName }
    }
    return $true
}

# ============================================================================
# 3. AUDIO DEVICE AUTO-DETECTION
# ============================================================================
function Detect-AudioDeviceAuto {
    Step "Detecting VB-Cable Audio Device"
    if ($script:State.AudioDeviceConfigured) { Ok "Already configured"; return $true }

    # Get all audio devices from mpv
    try {
        $mpvPath = (Get-Command mpv -ErrorAction Stop).Source
        $devices = & $mpvPath --audio-device=help 2>&1
        $vbDevice = $devices | Select-String "CABLE|VB-Cable|VB-Audio" | Select -First 1
        if ($vbDevice) {
            $name = $vbDevice.Line.Trim() -replace '^\s*\S+\s+', ''
            Ok "Found VB-Cable device: $name"
            $script:AudioDeviceName = $name
            $script:State.AudioDeviceConfigured = $true
        } else {
            Warn "VB-Cable device not found in mpv list. Run 'mpv --audio-device=help' after reboot."
        }
    } catch {
        Warn "Could not run mpv to detect audio devices"
    }
    return $true  # Don't fail installation if audio device not found yet
}

# ============================================================================
# 3. REPO + BUILD (staging-based: preserves user data)
# ============================================================================
# User data files that must survive an installer re-run:
#   config.toml, playlist.json, *.log, playlist_dir/*.json
$USER_DATA_GLOBS = @("config.toml", "playlist.json", "*.log")

function Backup-UserData {
    param([string]$Dir)
    $backup = Join-Path $env:TEMP "autodj-userdata-backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    if (-not (Test-Path $Dir)) { return $null }
    $found = $false
    foreach ($g in $USER_DATA_GLOBS) {
        Get-ChildItem -Path $Dir -Filter $g -File -ErrorAction SilentlyContinue | ForEach-Object {
            $dest = Join-Path $backup $_.Name
            Copy-Item $_.FullName -Destination $dest -Force
            $found = $true
        }
    }
    # Also back up any playlist_dir/*.json files
    if (Test-Path (Join-Path $Dir "playlist_dir") -PathType Container) {
        $pd = Join-Path $backup "playlist_dir"
        New-Item -ItemType Directory -Path $pd -Force | Out-Null
        Get-ChildItem -Path (Join-Path $Dir "playlist_dir") -Filter "*.json" -File -ErrorAction SilentlyContinue | ForEach-Object {
            Copy-Item $_.FullName -Destination (Join-Path $pd $_.Name) -Force
            $found = $true
        }
    }
    if ($found) { Ok "User data backed up to $backup"; return $backup }
    return $null
}

function Restore-UserData {
    param([string]$Dir, [string]$Backup)
    if (-not $Backup -or -not (Test-Path $Backup)) { return }
    Set-Location $Backup
    Get-ChildItem -File -ErrorAction SilentlyContinue | ForEach-Object {
        Copy-Item $_.FullName -Destination (Join-Path $Dir $_.Name) -Force
        Ok "Restored user data: $($_.Name)"
    }
    $pd = Join-Path $Backup "playlist_dir"
    if (Test-Path $pd -PathType Container) {
        $destPd = Join-Path $Dir "playlist_dir"
        New-Item -ItemType Directory -Path $destPd -Force | Out-Null
        Get-ChildItem -Path $pd -Filter "*.json" -File -ErrorAction SilentlyContinue | ForEach-Object {
            Copy-Item $_.FullName -Destination (Join-Path $destPd $_.Name) -Force
            Ok "Restored playlist: $($_.Name)"
        }
    }
}

function Setup-RepoAuto {
    Step "Setting up Repository & Building AutoDJ.exe"
    $backupDir = $null
    if (Test-Path $ProjectDir) {
        # Check for user data before any destructive operation
        $hasUserData = $false
        foreach ($g in $USER_DATA_GLOBS) {
            if (Get-ChildItem -Path $ProjectDir -Filter $g -File -ErrorAction SilentlyContinue | Select -First 1) { $hasUserData = $true; break }
        }
        if (-not $hasUserData) {
            $pd = Join-Path $ProjectDir "playlist_dir"
            if (Test-Path $pd -PathType Container -and (Get-ChildItem -Path $pd -Filter "*.json" -File -ErrorAction SilentlyContinue | Select -First 1)) { $hasUserData = $true }
        }

        if ($hasUserData) {
            $backupDir = Backup-UserData $ProjectDir
            if (-not $backupDir) { Fail "Failed to back up user data. Aborting to prevent data loss."; return $false }
        }

        if (-not $Unattended -and -not (Ask "Directory exists. Overwrite?")) { return $false }
        $BackupDir = "$ProjectDir.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        Move-Item $ProjectDir $BackupDir -ErrorAction SilentlyContinue
        Ok "Existing project backed up to $BackupDir (playlists, config, and logs preserved)"
    }
    Ok "Cloning repository..."
    git clone --depth 1 $REPO_URL $ProjectDir
    if (-not (Test-Path "$ProjectDir\run_autodj.py")) { Fail "Clone failed"; return $false }
    Ok "Repository ready at $ProjectDir"

    # Restore any backed-up user data into the fresh clone
    Restore-UserData $ProjectDir $backupDir

    if (-not $NoBuild) {
        Ok "Building AutoDJ.exe (this takes a minute)..."
        Set-Location $ProjectDir
        .\build.ps1 -NoSign  # Self-sign is fine for personal use
        if (-not (Test-Path "dist\AutoDJ.exe")) { Fail "Build failed"; return $false }
        Ok "AutoDJ.exe built at dist\AutoDJ.exe"
    }
    return $true
}

# ============================================================================
# 4. AUTO-CONFIG (Everything!)
# ============================================================================
function Auto-ConfigComplete {
    Step "Generating Complete Configuration"
    Set-Location $ProjectDir

    # Detect audio device if VB-Cable installed
    $audioDevice = ""
    if ($script:State.VBCableInstalled -or (Get-PnpDevice -Class MEDIA -EA SilentlyContinue | Where { $_.FriendlyName -like "*VB-Cable*" })) {
        $mpvPath = (Get-Command mpv -EA Stop).Source
        $devs = & $mpvPath --audio-device=help 2>&1
        $vb = $devs | Select-String "CABLE|VB-Cable|VB-Audio" | Select -First 1
        if ($vb) { $audioDevice = $vb.Line.Trim() -replace '^\s*\S+\s+', ''; Ok "Auto-detected audio device: $audioDevice" }
    }

    $audioMsg = if ($audioDevice) { "Audio device: $audioDevice" } else { 'Not set (install VB-Cable)' }

    # Build autoplay sources from query
    $queries = $PlaylistQuery -split ',' | ForEach { $_.Trim() }
    $autoplaySources = $queries | ForEach { "ytsearch20:$_" }

    # Build config line by line (avoid here-string issues)
    # Use forward slashes for TOML paths
    $mpvPath = (Get-Command mpv -EA Stop).Source -replace '\\', '/'
    $ytDlpPath = (Get-Command yt-dlp -EA Stop).Source -replace '\\', '/'
    $musicDir = ($env:USERPROFILE + '\Music') -replace '\\', '/'

    $configLines = @(
        '# AutoDJ Configuration'
        '# ============================'
        ''
        '# --- Core Bot Identity --------------------------------------------------------'
        'bot_nick = "AutoDJ"'
        'admins = ["Seaza"]'
        'prefix = "!"'
        'lang = "th"'
        ''
        '# --- Chat I/O (UI Automation / Log Tail / Console) ---------------------------'
        'chat_reader = "uia"'
        'chat_sender = "uia"'
        'auto_discover = true'
        'view_kind = "web"'
        'send_mode = "auto"'
        'send_verify = true'
        'web_strict_body = true'
        'web_view_title = "wb-log-room-data"'
        'web_input_title = "wb-edit-data"'
        'view_type = "Document"'
        'view_index = 0'
        'input_type = "Edit"'
        'input_index = -1'
        ''
        '# Log file (optional, for logtail reader or additional logging)'
        'log_path = ""'
        'log_encoding = "utf-8"'
        ''
        '# Line parsing regex for logtail reader (must have named groups: user, text)'
        "line_regex = '^(?:\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*)?(?P<user>[^:\s][^:]{0,30}):\s(?P<text>.+)$'"
        ''
        '# --- Media Playback (mpv / yt-dlp) -------------------------------------------'
        'audio_device = "' + $audioDevice + '"'
        'volume = 70'
        ''
        'mpv_path = "' + $mpvPath + '"'
        'ytdlp_path = "' + $ytDlpPath + '"'
        'youtube_cookies_file = ""'
        'youtube_cookies_browser = ""'
        'youtube_ca_bundle = ""'
        ''
        '# Audio engineering'
        'audio_fade = true'
        'audio_fade_in_sec = 1.2'
        'audio_fade_out_sec = 1.5'
        'audio_normalize = false'
        ''
        '# --- Local Music Library & TTS -----------------------------------------------'
        'music_dirs = ["' + $musicDir + '"]'
        'autoplay_sources = ['
    )
    foreach ($src in $autoplaySources) {
        $configLines += '    "' + $src + '",'
    }
    $configLines += ']'
    $configLines += 'shuffle = true'
    $configLines += ''
    $configLines += 'tts_voice = ""'
    $configLines += 'tts_rate = 170'
    $configLines += 'tts_duck = 25'
    $configLines += ''
    $configLines += '# --- Request / Queue Limits --------------------------------------------------'
    $configLines += 'allowed_hosts = ["youtube.com", "youtu.be", "music.youtube.com"]'
    $configLines += 'max_requests_per_user = 3'
    $configLines += 'max_queue = 50'
    $configLines += 'max_duration = 900'
    $configLines += 'voteskip_threshold = 3'
    $configLines += 'cooldown = 3.0'
    $configLines += 'send_interval = 1.5'
    $configLines += 'max_msg_len = 180'
    $configLines += 'announce_next = true'
    $configLines += ''
    $configLines += 'msg_now = ""'
    $configLines += 'msg_next = ""'
    $configLines += ''
    $configLines += '# --- Auto Launch (Windows) ----------------------------------------------------'
    $configLines += 'auto_launch = false'
    $configLines += 'camfrog_exe = ""'
    $configLines += 'client_title_re = ".*"'
    $configLines += 'room = "AutoDJ"'
    $configLines += 'join_uri_template = ""'
    $configLines += 'launch_timeout = 60'
    $configLines += ''
    $configLines += '# --- Moderation & Security ----------------------------------------------------'
    $configLines += 'blocked_users = []'
    $configLines += ''
    $configLines += 'poll_interval = 0.5'
    $configLines += 'im_require_room_presence = true'
    $configLines += 'allow_play_in_room = false'
    $configLines += ''
    $configLines += '# --- Logging ------------------------------------------------------------------'
    $configLines += 'log_file = "autodj.log"'
    $configLines += 'log_json = false'
    $configLines += 'log_json_fields = ['
    $configLines += '  "request_id", "delivery_id", "user", "track_id", "generation",'
    $configLines += '  "attempt_id", "category", "stage", "state"'
    $configLines += ']'
    $configLines += ''
    $configLines += '# --- Playlist Persistence -----------------------------------------------------'
    $configLines += 'playlist_file = "playlist.json"'
    $configLines += 'playlist_dir = ""'
    $configLines += ''
    $configLines += '# --- YouTube Search -----------------------------------------------------------'
    $configLines += 'search_limit = 1'
    $configLines += ''
    $configLines += '# --- mpv Hang Detection -------------------------------------------------------'
    $configLines += 'mpv_timeout = 120'
    $configLines += ''
    $configLines += '# --- Dynamic Moderation -------------------------------------------------------'
    $configLines += 'voteskip_dynamic = false'
    $configLines += 'voteskip_dynamic_pct = 30'
    $configLines += 'user_request_limit = 5'
    $configLines += 'rate_limit_window = 300.0'
    $configLines += ''
    $configLines += '# --- Auto-reply (Scheduled Ads/Messages) --------------------------------------'
    $configLines += 'auto_reply_enabled = true'
    $configLines += 'auto_reply_interval = 60.0'
    $configLines += 'auto_reply_file = "ads-list.json"'
    $configLines += ''
    '# IM Auto-reply: automatic reply to private/instant messages'
    $configLines += 'im_auto_reply_enabled = true'
    $configLines += 'im_auto_reply_message = "Thanks for your message! I am a bot and will respond when I can. Use !help for commands."'
    $configLines += 'im_auto_reply_cooldown = 60.0'
    $configLines += ''
    $configLines += '# --- Autoplay: Switch to Autoplay Pool After Idle Timeout ---------------------'
    $configLines += 'autoplay_idle_timeout = 30.0'
    $configLines += ''
    $configLines += '# --- Admin Greeting -----------------------------------------------------------'
    $configLines += 'admin_greeting_enabled = true'
    $configLines += 'admin_greeting_message = "สวัสดีครับแอดมิน {admin} ยินดีต้อนรับกลับมา!"'
    $configLines += 'admin_greeting_cooldown = 3600.0'
    $configLines += ''
    $configLines += '# --- IM Viewer ----------------------------------------------------------------'
    $configLines += 'im_viewer_enabled = true'
    $configLines += ''
    $configLines += '# --- Font/Style Customization (GUI Preview Only) ------------------------------'
    $configLines += 'message_style = { font_family = "Tahoma", font_size = 14, font_color = "#FF0000", bold = true, italic = false, underline = false }'
    $configLines += ''
    $configLines += '# --- Admin Mic Mute/Unmute (Config-Gated) -------------------------------------'
    $configLines += 'admin_mute_mic = true'
    $configLines += 'admin_unmute_mic = true'
    $configLines += ''
    $configLines += '# --- Block/Unblock User (Config-Gated) ----------------------------------------'
    $configLines += 'admin_block_user = false'
    $configLines += 'admin_unblock_user = false'
    $configLines += ''
    $configLines += '# --- Mic Mute State -----------------------------------------------------------'
    $configLines += 'mute_enabled = false'
    $configLines += ''
    $configLines += '# --- Block/Unblock Bot (Config-Gated) -----------------------------------------'
    $configLines += 'admin_block_bot = true'
    $configLines += 'admin_unblock_bot = true'
    $configLines += ''
    $configLines += '# --- Kick/Ban/Unban User (Config-Gated) ---------------------------------------'
    $configLines += 'admin_kick_user = true'
    $configLines += 'admin_ban_user = true'
    $configLines += 'admin_unban_user = true'
    $configLines += ''
    $configLines += '# --- Punish User/Bot (Config-Gated) -------------------------------------------'
    $configLines += 'admin_punish_user = true'
    $configLines += 'admin_punish_bot = true'
    $configLines += ''
    $configLines += '# --- Delete Message (Config-Gated) --------------------------------------------'
    $configLines += 'admin_delete_message_enabled = true'
    $configLines += ''
    $configLines += '# --- Welcome Message ----------------------------------------------------------'
    $configLines += 'welcome_message_enabled = true'
    $configLines += 'welcome_message_message = "ยินดีต้อนรับสู่ห้องแชทของ AutoDJ!"'
    $configLines += 'welcome_message_cooldown = 3600.0'
    $configLines += ''
    $configLines += '# --- Camfrog RE Integrations (Gift / Avatar / Status / Status Alert) ----------'
    $configLines += 'gift_announce_enabled = true'
    $configLines += 'avatar_change_enabled = true'
    $configLines += 'status_indicator_enabled = true'
    $configLines += 'status_alert_enabled = true'
    $configLines += ''
    $configLines += '# --- Webhook / API Integration ------------------------------------------------'
    $configLines += 'webhook_enabled = false'
    $configLines += 'webhook_host = "127.0.0.1"'
    $configLines += 'webhook_port = 8080'
    $configLines += 'webhook_secret = ""'
    $configLines += 'webhook_rate_limit_per_ip = 60'
    $configLines += 'webhook_cors_origins = ["*"]'
    $configLines += ''
    $configLines += '# --- Config Hot Reload --------------------------------------------------------'
    $configLines += 'config_hot_reload = false'
    $configLines += ''
    $configLines += '# --- Plugin System ------------------------------------------------------------'
    $configLines += 'plugins = ["builtin.stats", "builtin.help"]'

    $config = $configLines -join "`n"

    $configPath = Join-Path $ProjectDir "config.toml"
    $config | Set-Content -Path $configPath -Encoding utf8
    # Ensure dist directory exists (created by build, but may not exist with -NoBuild)
    if (-not (Test-Path "$ProjectDir\dist")) { New-Item -ItemType Directory -Path "$ProjectDir\dist" | Out-Null }
    Copy-Item $configPath "$ProjectDir\dist\config.toml" -Force
    $script:State.ConfigComplete = $true
    $audioMsg = if ($audioDevice) { "Audio device: $audioDevice" } else { 'Not set (install VB-Cable)' }
    Ok "config.toml generated with:"
    Ok "  - mpv/yt-dlp paths auto-detected"
    Ok "  - $audioMsg"
    Ok "  - autoplay_sources: $($autoplaySources.Count) search queries"
    return $true
}

# ============================================================================
# 5. SHORTCUTS + AUTO-START
# ============================================================================
function Create-ShortcutsAuto {
    if ($NoShortcuts) { return $true }
    Step "Creating Shortcuts"
    $exe = "$ProjectDir\dist\AutoDJ.exe"
    $ico = "$ProjectDir\app.ico"
    $wsh = New-Object -ComObject WScript.Shell

    # Desktop
    $deskDir = [Environment]::GetFolderPath("Desktop")
    $deskPath = Join-Path $deskDir "AutoDJ.lnk"
    $desk = $wsh.CreateShortcut($deskPath)
    $desk.TargetPath = $exe; $desk.Arguments = "--gui"; $desk.WorkingDirectory = "$ProjectDir\dist"; $desk.IconLocation = $ico; $desk.Save()
    Ok "Desktop shortcut"

    # Start Menu
    $sm = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\AutoDJ"
    New-Item -ItemType Directory -Path $sm -Force | Out-Null
    $s1Path = Join-Path $sm "AutoDJ.lnk"
    $s1 = $wsh.CreateShortcut($s1Path)
    $s1.TargetPath = $exe; $s1.Arguments = "--gui"; $s1.WorkingDirectory = "$ProjectDir\dist"; $s1.IconLocation = $ico; $s1.Save()
    $s2Path = Join-Path $sm "Edit Config.lnk"
    $s2 = $wsh.CreateShortcut($s2Path)
    $s2.TargetPath = "notepad.exe"; $s2.Arguments = "$ProjectDir\config.toml"; $s2.Save()
    $s3Path = Join-Path $sm "Uninstall.lnk"
    $s3 = $wsh.CreateShortcut($s3Path)
    $s3.TargetPath = "powershell.exe"; $s3.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$ProjectDir\uninstall.ps1`""; $s3.Save()
    Ok "Start Menu shortcuts"

    # Auto-start
    if (-not $NoAutoStart) {
        $startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
        $st = Join-Path $startupDir "AutoDJ.lnk"
        $sa = $wsh.CreateShortcut($st)
        $sa.TargetPath = $exe; $sa.Arguments = "--gui"; $sa.WorkingDirectory = "$ProjectDir\dist"; $sa.IconLocation = $ico; $sa.Save()
        Ok "Auto-start shortcut"
    }
    return $true
}

# ============================================================================
# 6. UNINSTALLER
# ============================================================================
function Create-UninstallerAuto {
    $content = @"
<#
.SYNOPSIS
    AutoDJ Uninstaller
#>
param([switch]`$Force)
`$ErrorActionPreference = "Continue"
`$Proj = "$ProjectDir"
Write-Host "Uninstalling AutoDJ..." -Fore Cyan

# Shortcuts
`$sm = Join-Path `$env:APPDATA "Microsoft\Windows\Start Menu\Programs\AutoDJ"
if (Test-Path `$sm) { Remove-Item -Recurse -Force `$sm; "Removed Start Menu" }
`$desk = Join-Path [Environment]::GetFolderPath("Desktop") "AutoDJ.lnk"
if (Test-Path `$desk) { Remove-Item -Force `$desk; "Removed Desktop" }
`$st = Join-Path `$env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup\AutoDJ.lnk"
if (Test-Path `$st) { Remove-Item -Force `$st; "Removed Auto-start" }

# Project dir
if (`$Force -or (Read-Host "Remove `$Proj? [y/N]" -eq "y")) {
    if (Test-Path `$Proj) { Remove-Item -Recurse -Force `$Proj; "Removed project dir" }
}

Write-Host "Uninstall complete." -Fore Green
Read-Host "Press Enter"
"@
    Set-Content (Join-Path $ProjectDir "uninstall.ps1") -Value $content -Encoding utf8
    Ok "Uninstaller created"
}

# ============================================================================
# 7. VERIFICATION
# ============================================================================
function Verify-All {
    Step "Final Verification"
    $exePath = "$ProjectDir\dist\AutoDJ.exe"
    if (-not (Test-Path $exePath)) {
        Warn "AutoDJ.exe not found (build skipped with -NoBuild). Skipping verification."
        return $true
    }
    Set-Location "$ProjectDir\dist"
    $tempOut = [System.IO.Path]::GetTempFileName()
    $tempErr = [System.IO.Path]::GetTempFileName()
    $proc = Start-Process $exePath -ArgumentList "--check" -Wait -PassThru -NoNewWindow -RedirectStandardOutput $tempOut -RedirectStandardError $tempErr
    $exitCode = $proc.ExitCode
    $stdout = Get-Content $tempOut
    $stderr = Get-Content $tempErr
    Remove-Item $tempOut, $tempErr -Force -ErrorAction SilentlyContinue

    $allOutput = $stdout + $stderr
    foreach ($line in $allOutput) {
        if ($line -match "^\[ ?(OK|INFO|WARN|FAIL) ?\]") {
            $lvl = $matches[1]; $msg = $line -replace "^\[ ?(OK|INFO|WARN|FAIL) ?\]\s*",""
            switch ($lvl) { "OK" { Ok $msg } "INFO" { Write-Host "  $msg" -Fore $C_GRAY } "WARN" { Warn $msg } "FAIL" { Fail $msg } }
        } elseif ($line -match "^\[\d{4}-\d{2}-\d{2}") { Write-Host "  $line" -Fore $C_GRAY }
    }
    if ($exitCode -eq 0) { Ok "ALL CHECKS PASSED"; return $true } else { Fail "Some checks failed (exit code: $exitCode)"; return $false }
}

# ============================================================================
# MAIN
# ============================================================================
Write-Host ""
Write-Host ("="*72) -Fore $C_CYAN
Write-Host "  AutoDJ - FULLY AUTOMATED INSTALLER" -Fore $C_CYAN
Write-Host ("="*72) -Fore $C_CYAN
Write-Host ""

if (-not (IsAdmin)) { Fail "MUST RUN AS ADMINISTRATOR. Right-click PowerShell -> Run as Administrator."; exit 1 }

# Handle reboot-after-VB-Cable
if ($script:State.RebootRequired) {
    Warn "REBOOT REQUIRED for VB-Cable. Please reboot now, then run this script again."
    if (Ask "Reboot now?") { Restart-Computer -Force }
    exit 0
}

# Pipeline
$success = $true
$success = $success -and (Install-VBCableAuto)
$success = $success -and (Install-DepsAuto)
$success = $success -and (Setup-RepoAuto)
$success = $success -and (Detect-AudioDeviceAuto)
$success = $success -and (Auto-ConfigComplete)
$success = $success -and (Create-ShortcutsAuto)
Create-UninstallerAuto
$success = $success -and (Verify-All)

# Summary
Write-Host ""; Write-Host ("="*72) -Fore $C_CYAN
Write-Host "  INSTALLATION COMPLETE" -Fore $C_CYAN
Write-Host ("="*72) -Fore $C_CYAN
Write-Host ""
if ($success) {
    Ok "AutoDJ is ready!"
    Write-Host ""
    Write-Host "Next steps:" -Fore $C_CYAN
    Write-Host "  1. Open Camfrog and join your room" -Fore $C_WHITE
    Write-Host "  2. Run AutoDJ from Desktop/Start Menu or:" -Fore $C_WHITE
    Write-Host "     cd $ProjectDir\dist" -Fore $C_GRAY
    Write-Host "     .\AutoDJ.exe --gui" -Fore $C_GRAY
    Write-Host ""
    if (-not $script:State.VBCableInstalled) {
        Warn "VB-Cable not installed - audio won't route to Camfrog mic!"
        Write-Host "  Install from: $VBCABLE_URL" -Fore $C_GRAY
    }
} else {
    Fail "Installation had issues. Check log: $LOG_FILE"
}
Read-Host "Press Enter to exit"
