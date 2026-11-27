<#
.SYNOPSIS
Move an existing AutoDJ install (before 0.4.0) over to the zAutoDJ name.

.DESCRIPTION
Run by the zAutoDJ installer after zAutoDJ.exe is in place; safe to run again.
Only things that point into -InstallDir are touched:
  * shortcuts (.lnk) in -ShortcutRoots whose target is <InstallDir>\AutoDJ.exe are
    re-pointed to zAutoDJ.exe; ones named AutoDJ / CamfrogAutoDJ are renamed zAutoDJ
  * HKCU App Paths\AutoDJ.exe pointing at <InstallDir>\AutoDJ.exe is removed
  * HKCU Uninstall entries other than "zAutoDJ" whose InstallLocation is <InstallDir>
    are removed (the installer writes the zAutoDJ one)
  * HKCU\Software\AutoDJ InstallDir/mpv_path/ytdlp_path for this folder are removed
  * <InstallDir>\AutoDJ.exe and AutoDJ.exe.next are deleted
Config, logs, playlists and *.bak files are never touched.
#>
param(
    [Parameter(Mandatory = $true)][string]$InstallDir,
    [string[]]$ShortcutRoots = @(
        [Environment]::GetFolderPath('Desktop'),
        [Environment]::GetFolderPath('Programs'),
        [Environment]::GetFolderPath('Startup')
    ),
    [string]$RegistryRoot = 'HKCU:\Software'
)
$ErrorActionPreference = 'Continue'
# GetFullPath also expands 8.3 short names (C:\Users\ABCDEF~1): compare full paths only
function Norm([string]$p) {
    if (-not $p) { return '' }
    try { return [IO.Path]::GetFullPath($p).TrimEnd('\') } catch { return $p }
}
$dir = Norm $InstallDir
$oldExe = Join-Path $dir 'AutoDJ.exe'
$newExe = Join-Path $dir 'zAutoDJ.exe'
if (-not (Test-Path -LiteralPath $newExe)) {
    Write-Output "zAutoDJ.exe not found in ${dir}: nothing migrated"
    exit 0
}

$shell = New-Object -ComObject WScript.Shell
foreach ($root in $ShortcutRoots) {
    if (-not $root -or -not (Test-Path -LiteralPath $root)) { continue }
    foreach ($f in Get-ChildItem -LiteralPath $root -Filter *.lnk -Recurse -ErrorAction SilentlyContinue) {
        $lnk = $shell.CreateShortcut($f.FullName)
        if ((Norm $lnk.TargetPath) -ine $oldExe) { continue }
        $lnk.TargetPath = $newExe
        $lnk.Save()
        Write-Output "shortcut re-pointed: $($f.FullName)"
        if ($f.BaseName -in @('AutoDJ', 'CamfrogAutoDJ')) {
            $dest = Join-Path $f.DirectoryName 'zAutoDJ.lnk'
            if (-not (Test-Path -LiteralPath $dest)) {
                Rename-Item -LiteralPath $f.FullName -NewName 'zAutoDJ.lnk'
                Write-Output "shortcut renamed: $dest"
            }
        }
    }
}

$appPath = Join-Path $RegistryRoot 'Microsoft\Windows\CurrentVersion\App Paths\AutoDJ.exe'
if ((Test-Path $appPath) -and ((Norm (Get-ItemProperty $appPath).'(default)') -ieq $oldExe)) {
    Remove-Item $appPath -Recurse
    Write-Output "removed App Paths\AutoDJ.exe"
}

$uninst = Join-Path $RegistryRoot 'Microsoft\Windows\CurrentVersion\Uninstall'
if (Test-Path $uninst) {
    foreach ($k in Get-ChildItem $uninst) {
        if ($k.PSChildName -eq 'zAutoDJ') { continue }
        $loc = (Get-ItemProperty $k.PSPath).InstallLocation
        if ($loc -and ((Norm $loc) -ieq $dir)) {
            Remove-Item $k.PSPath -Recurse
            Write-Output "removed Uninstall\$($k.PSChildName)"
        }
    }
}

$legacy = Join-Path $RegistryRoot 'AutoDJ'
if ((Test-Path $legacy) -and ((Norm (Get-ItemProperty $legacy).InstallDir) -ieq $dir)) {
    foreach ($v in 'InstallDir', 'mpv_path', 'ytdlp_path') {
        Remove-ItemProperty $legacy -Name $v -ErrorAction SilentlyContinue
    }
    if (-not (Get-Item $legacy).Property -and -not (Get-ChildItem $legacy)) { Remove-Item $legacy }
    Write-Output "removed Software\AutoDJ values for $dir"
}

foreach ($f in $oldExe, "$oldExe.next") {
    if (Test-Path -LiteralPath $f) {
        Remove-Item -LiteralPath $f -Force
        Write-Output "deleted $f"
    }
}
exit 0
