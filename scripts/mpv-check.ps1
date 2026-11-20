# Checks if mpv.exe is available on the system
param([int]$MinBuild = 22000)

$mpv_found = $false

# Check common locations
$mpv_paths = @(
    "mpv.exe",  # in PATH
    "C:\Program Files\mpv\mpv.exe",
    "C:\Program Files (x86)\mpv\mpv.exe",
    "$env:ProgramFiles\mpv\mpv.exe"
)

foreach ($path in $mpv_paths) {
    if (Test-Path $path) {
        Write-Host "  OK: mpv.exe found at $path"
        $mpv_found = $true
        break
    }
}

if (-not $mpv_found) {
    Write-Host "WARN: mpv.exe not found. Install: choco install mpv --yes"
}

# Output log line
Write-Output "mpv check completed" >> "$env:BUILD_LOG_DIR\win11-check-$env:BUILD_LOG_TS.log" 2>$null