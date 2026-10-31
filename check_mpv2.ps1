# Check if mpv is in the winget package directory
$wingetDir = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\mpv-player.mpv-CI.MSVC*"
Get-ChildItem $wingetDir -Recurse -Filter mpv.exe -ErrorAction SilentlyContinue