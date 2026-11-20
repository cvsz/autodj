# Checks if PyInstaller is available
param([int]$MinBuild = 22000)

$pyinstaller_found = $false

# Check if PyInstaller is installed
try {
    & $(PY) -c "import PyInstaller"
    Write-Host "  OK: PyInstaller installed"
    $pyinstaller_found = $true
} catch {
    Write-Host "WARN: PyInstaller not installed. Run: $(PIP) install pyinstaller"
}

# Output log line
Write-Output "PyInstaller check completed" >> "$env:BUILD_LOG_DIR\win11-check-$env:BUILD_LOG_TS.log" 2>$null