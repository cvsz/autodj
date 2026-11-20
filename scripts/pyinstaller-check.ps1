# Reports whether PyInstaller is importable by the build's Python.
# Warning only (exit 0); the pyinstaller-check make target is the hard gate.
# Output goes to stdout; the Makefile appends it to the build log.
param([string]$Python = "python")

$ok = $false
try {
    & $Python -c "import PyInstaller" 2>$null
    # A native command that fails does not throw: check its exit code.
    $ok = ($LASTEXITCODE -eq 0)
} catch {
    $ok = $false  # $Python itself could not be started
}

if ($ok) {
    Write-Output "  OK: PyInstaller installed"
} else {
    Write-Output "WARN: PyInstaller not installed for '$Python'. Run: $Python -m pip install pyinstaller"
}
exit 0
