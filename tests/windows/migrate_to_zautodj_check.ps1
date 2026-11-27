# Sandbox check for tools/migrate_to_zautodj.ps1 (run by tests/test_migrate_to_zautodj.py).
# Uses a temp folder and HKCU:\Software\zautodj-migrate-test only; both are removed.
param([Parameter(Mandatory = $true)][string]$MigrateScript)
$ErrorActionPreference = 'Stop'
$t = Join-Path ([IO.Path]::GetFullPath($env:TEMP)) ("zmig-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
$inst = Join-Path $t 'D CamfrogAutoDJ'
$other = Join-Path $t 'other'
$sc = Join-Path $t 'shortcuts'
New-Item -ItemType Directory $inst, $other, "$sc\Programs\CamfrogAutoDJ" | Out-Null
'old' | Set-Content "$inst\AutoDJ.exe"; 'new' | Set-Content "$inst\zAutoDJ.exe"; 'cfg' | Set-Content "$inst\config.toml"
'x' | Set-Content "$other\AutoDJ.exe"
$sh = New-Object -ComObject WScript.Shell
function mk($p, $target) { $l = $sh.CreateShortcut($p); $l.TargetPath = $target; $l.Arguments = '--gui'; $l.Save() }
mk "$sc\CamfrogAutoDJ.lnk" "$inst\AutoDJ.exe"
mk "$sc\Programs\CamfrogAutoDJ\CamfrogAutoDJ.lnk" "$inst\AutoDJ.exe"
mk "$sc\Mine.lnk" "$inst\AutoDJ.exe"
mk "$sc\Other.lnk" "$other\AutoDJ.exe"
$rr = 'HKCU:\Software\zautodj-migrate-test'
$u = "$rr\Microsoft\Windows\CurrentVersion\Uninstall"
New-Item "$u\CamfrogAutoDJ" -Force | Out-Null; Set-ItemProperty "$u\CamfrogAutoDJ" InstallLocation $inst
New-Item "$u\SomethingElse" -Force | Out-Null; Set-ItemProperty "$u\SomethingElse" InstallLocation $other
New-Item "$u\zAutoDJ" -Force | Out-Null; Set-ItemProperty "$u\zAutoDJ" InstallLocation $inst
$ap = "$rr\Microsoft\Windows\CurrentVersion\App Paths\AutoDJ.exe"
New-Item $ap -Force | Out-Null; Set-ItemProperty $ap '(default)' "$inst\AutoDJ.exe"
New-Item "$rr\AutoDJ" -Force | Out-Null; Set-ItemProperty "$rr\AutoDJ" InstallDir $inst; Set-ItemProperty "$rr\AutoDJ" mpv_path "$inst\mpv\mpv.exe"
try {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $MigrateScript -InstallDir $inst -ShortcutRoots $sc -RegistryRoot $rr
    "--- second run (idempotent)"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $MigrateScript -InstallDir $inst -ShortcutRoots $sc -RegistryRoot $rr
    "--- checks"
    $ok = $true
    function chk($cond, $what) { if ($cond) { "PASS $what" } else { "FAIL $what"; $script:ok = $false } }
    chk (-not (Test-Path "$inst\AutoDJ.exe")) 'old exe deleted'
    chk ((Test-Path "$inst\zAutoDJ.exe") -and (Test-Path "$inst\config.toml")) 'new exe + config kept'
    chk (Test-Path "$other\AutoDJ.exe") 'other install untouched'
    chk ($sh.CreateShortcut("$sc\zAutoDJ.lnk").TargetPath -ieq "$inst\zAutoDJ.exe") 'desktop lnk renamed + re-pointed'
    chk ($sh.CreateShortcut("$sc\zAutoDJ.lnk").Arguments -eq '--gui') 'arguments kept'
    chk (Test-Path "$sc\Programs\CamfrogAutoDJ\zAutoDJ.lnk") 'start menu lnk renamed'
    chk ($sh.CreateShortcut("$sc\Mine.lnk").TargetPath -ieq "$inst\zAutoDJ.exe") 'custom-named lnk re-pointed, name kept'
    chk ($sh.CreateShortcut("$sc\Other.lnk").TargetPath -ieq "$other\AutoDJ.exe") 'other lnk untouched'
    chk (-not (Test-Path "$u\CamfrogAutoDJ")) 'old uninstall entry removed'
    chk (Test-Path "$u\SomethingElse") 'unrelated uninstall entry kept'
    chk (Test-Path "$u\zAutoDJ") 'zAutoDJ uninstall entry kept'
    chk (-not (Test-Path $ap)) 'old App Paths removed'
    chk (-not (Test-Path "$rr\AutoDJ")) 'legacy Software\AutoDJ removed'
    "ALL=$ok"
} finally {
    Remove-Item $rr -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $t -Recurse -Force -ErrorAction SilentlyContinue
    "cleanup: registry test key exists=$(Test-Path $rr) temp exists=$(Test-Path $t)"
}
