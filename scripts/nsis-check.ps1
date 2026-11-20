# Checks if NSIS makensis is available on the system
param([int]$MinBuild = 22000)

$nsis_found = $false

# Check common locations
$nsis_paths = @(
    "makensis.exe",  # in PATH
    "C:\Program Files (x86)\NSIS\makensis.exe",
    "C:\Program Files\NSIS\makensis.exe"
)

foreach ($path in $nsis_paths) {
    if (Test-Path $path) {
        Write-Host "  OK: NSIS makensis found at $path"
        $nsis_found = $true
        break
    }
}

if (-not $nsis_found) {
    Write-Host "ERROR: NSIS (makensis) not found. Install NSIS 3.09+ (choco install nsis) or set SKIP_CHECKS=1 to bypass."
}

# Output log line
Write-Output "NSIS check completed" >> "$env:BUILD_LOG_DIR\win11-check-$env:BUILD_LOG_TS.log" 2>$null