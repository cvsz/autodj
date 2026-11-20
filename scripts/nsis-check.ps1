# Fails (exit 1) unless NSIS makensis.exe is available: the installer cannot be
# built without it.  Output goes to stdout; the Makefile appends it to the build log.

$found = $null
$cmd = Get-Command makensis.exe -ErrorAction SilentlyContinue
if ($cmd) {
    $found = $cmd.Source
} else {
    foreach ($path in @(
            "C:\Program Files (x86)\NSIS\makensis.exe",
            (Join-Path $env:ProgramFiles "NSIS\makensis.exe")
        )) {
        if ($path -and (Test-Path -LiteralPath $path -PathType Leaf)) {
            $found = $path
            break
        }
    }
}

if ($found) {
    Write-Output "  OK: NSIS makensis found at $found"
    exit 0
}
Write-Output "ERROR: NSIS (makensis) not found. Install NSIS 3.09+ (choco install nsis) or set SKIP_CHECKS=1 to bypass."
exit 1
