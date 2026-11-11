# Fails (exit 1) unless the OS build number is >= -MinBuild (22000 = Windows 11 21H2).
# Lives in a .ps1 so the Makefile never has to pass `$` / quote characters through
# bash, cmd.exe or sh -- that quoting is shell-specific and was the source of false
# "Not Windows 11" failures.
param([int]$MinBuild = 22000)

# Windows PowerShell 5.1 inheriting PowerShell 7 module dirs can break provider/module loading
# (same cause as the Get-AuthenticodeSignature failure). Drop PS7-only dirs.
if ($PSVersionTable.PSVersion.Major -le 5) {
    $env:PSModulePath = ($env:PSModulePath -split ';' | Where-Object {
        $_ -and $_ -notmatch 'PowerShell[\\/]7[\\/]Modules' -and
        $_ -notmatch 'Documents[\\/]PowerShell[\\/]Modules' -and
        $_ -notmatch 'Program Files[\\/]PowerShell[\\/]Modules'
    }) -join ';'
}

# Read the build via .NET (no provider/module needed), fall back to OSVersion.
$build = 0
try {
    $raw = [Microsoft.Win32.Registry]::GetValue('HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion', 'CurrentBuildNumber', $null)
    if ($raw) { $build = [int]$raw }
} catch { }
if ($build -le 0) { $build = [Environment]::OSVersion.Version.Build }

Write-Host "OS Build: $build"
if ($build -lt $MinBuild) {
    Write-Host "ERROR: Windows 11 (build $MinBuild+) required, found build $build"
    exit 1
}
exit 0
