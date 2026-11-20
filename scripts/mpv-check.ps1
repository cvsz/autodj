# Reports whether mpv.exe is available for Windows builds.
# Warning only (exit 0): the installer's mpv component is optional.
# Output goes to stdout; the Makefile appends it to the build log.
param([string]$BundleExe = "")

$found = $null
$cmd = Get-Command mpv.exe -ErrorAction SilentlyContinue
if ($cmd) {
    $found = $cmd.Source
} else {
    $candidates = @(
        (Join-Path $env:ProgramFiles "mpv\mpv.exe"),
        "C:\Program Files (x86)\mpv\mpv.exe"
    )
    if ($BundleExe) { $candidates += $BundleExe }
    foreach ($path in $candidates) {
        if ($path -and (Test-Path -LiteralPath $path -PathType Leaf)) {
            $found = $path
            break
        }
    }
}

if ($found) {
    Write-Output "  OK: mpv.exe found at $found"
} else {
    $extra = if ($BundleExe) { " (also checked $BundleExe)" } else { "" }
    Write-Output "WARN: mpv.exe not found$extra. Install: choco install mpv --yes"
}
exit 0
