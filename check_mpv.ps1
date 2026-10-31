# Check common winget install locations
$paths = @(
    "$env:LOCALAPPDATA\Microsoft\WindowsApps\mpv.exe",
    "$env:ProgramFiles\mpv\mpv.exe",
    "$env:ProgramFiles(x86)\mpv\mpv.exe",
    "$env:USERPROFILE\AppData\Local\Microsoft\WindowsApps\mpv.exe"
)
foreach ($p in $paths) {
    if (Test-Path $p) { Write-Host "Found: $p" }
}
# Check WindowsApps folder
Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WindowsApps\*mpv*" -ErrorAction SilentlyContinue