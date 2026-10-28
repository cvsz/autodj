<#
 AutoDJ: ONE script for build + sign.   usage (PowerShell, in the project folder):
     .\build.ps1                 build dist\AutoDJ.exe and sign it
     .\build.ps1 -Clean          delete build\, dist\ and AutoDJ.spec first (use after changing icon / version / options)
     .\build.ps1 -NoSign         build only
     .\build.ps1 -Pfx cert\x.pfx -Password "..."     sign with a purchased certificate (or env AUTODJ_PFX / AUTODJ_PFX_PASSWORD)
     .\build.ps1 -Thumbprint <hex>                 sign with a certificate already in your store (or env AUTODJ_CERT_THUMBPRINT)
 With none of those it uses (or creates, once) a SELF-SIGNED cert for -Subject in CurrentUser\My and trusts it on
 this machine (Root + TrustedPublisher; Windows shows one confirmation dialog). A self-signed cert is only trusted
 where its .cer is imported; for other people's PCs / no SmartScreen warning you need a real code-signing certificate.
 Inputs kept next to this file: app.ico, version_info.txt (company / product text), run_autodj.py, config.toml.
 Before building it checks that every package the exe must contain is installed in the `python` it will use
 (tools\check_build_env.py), and after building it starts the exe once (--version) as a smoke test.
#>
param(
  [switch]$Clean,
  [switch]$NoSign,
  [string]$Pfx = $env:AUTODJ_PFX,
  [string]$Password = $env:AUTODJ_PFX_PASSWORD,
  [string]$Thumbprint = $env:AUTODJ_CERT_THUMBPRINT,
  [string]$Subject = "CN=ZEAZDEV COMPANY LIMITED, O=ZEAZDEV COMPANY LIMITED, C=TH",
  [string]$Name = "AutoDJ"
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if ($PSVersionTable.PSVersion.Major -le 5) {
  # Windows PowerShell 5.1 may resolve PowerShell 7 module dirs (installed by pwsh 7 / VSCode tooling) and then fail
  # to load ITS OWN Microsoft.PowerShell.Security ("AuthorizationManager check failed") -- the Certificate provider
  # never registers, Cert: does not exist and the sign step dies.  Drop PS7-only dirs so 5.1 resolves its own modules.
  $env:PSModulePath = ($env:PSModulePath -split ';' | Where-Object {
    $_ -and $_ -notmatch 'PowerShell[\\/]7[\\/]Modules' -and
    $_ -notmatch 'Documents[\\/]PowerShell[\\/]Modules' -and
    $_ -notmatch 'Program Files[\\/]PowerShell[\\/]Modules'
  }) -join ';'
}
$exe = "dist\$Name.exe"

function Step($t) { Write-Host "`n== $t" -ForegroundColor Cyan }

# ---------- 0. sanity -------------------------------------------------------------------------------
foreach ($f in "run_autodj.py", "app.ico", "version_info.txt", "camfrog_autodj\__init__.py") {
  if (-not (Test-Path $f)) { throw "missing $f" }
}
if (Select-String -Path "camfrog_autodj\__init__.py" -Pattern "from \.base" -Quiet) {
  throw "camfrog_autodj\__init__.py contains the adapters __init__ content (from .base ...); it must only hold __version__"
}
if (Get-Process -Name $Name -ErrorAction SilentlyContinue) { throw "$Name.exe is running: close it first (it cannot be rebuilt or signed while open)" }

# ---------- 1. build --------------------------------------------------------------------------------
Step "check build environment"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "python was not found on PATH" }
& python tools\check_build_env.py
if ($LASTEXITCODE -ne 0) { throw "the Python used for the build is missing packages (see above): the exe would start but fail at run time" }

Step "build"
if ($Clean) { Remove-Item -Recurse -Force build, dist, "$Name.spec" -ErrorAction SilentlyContinue }
# yt_dlp loads its site extractors dynamically, hence --collect-all; pyttsx3 picks its speech driver at run time.
# --noupx: UPX-packed exes trigger far more antivirus false positives and start slower.
$pyi = @("--noconfirm", "--onefile", "--noupx", "--name", $Name, "--icon", "app.ico", "--version-file", "version_info.txt",
         "--add-data", "app.ico;.", "--collect-submodules", "camfrog_autodj",
         "--collect-submodules", "pywinauto", "--collect-submodules", "pyttsx3", "--collect-all", "yt_dlp",
         "--hidden-import", "comtypes", "--hidden-import", "pyperclip", "--hidden-import", "mutagen",
         "run_autodj.py")
& python -m PyInstaller @pyi   # same interpreter that was just checked (a `pyinstaller` on PATH may belong to another Python)
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $exe)) { throw "PyInstaller failed" }
if (Test-Path config.toml) { Copy-Item config.toml dist\config.toml -Force; "copied config.toml -> dist\" }

Step "smoke test"
& $exe --version
if ($LASTEXITCODE -ne 0) { throw "the built exe does not start (see the error above)" }
"tip: run  $exe --check  to verify mpv, yt-dlp, folders and the Camfrog window."

# ---------- 2. certificate + sign -------------------------------------------------------------------
if ($NoSign) { "`n(not signed: -NoSign)"; return }
Step "sign"
$cert = $null
if ($Pfx) {
  $sec = if ($Password) { ConvertTo-SecureString $Password -AsPlainText -Force } else { $null }
  $cert = Get-PfxCertificate -FilePath $Pfx -Password $sec
} elseif ($Thumbprint) {
  $tp = $Thumbprint -replace "\s", ""
  $cert = Get-ChildItem Cert:\CurrentUser\My, Cert:\LocalMachine\My | Where-Object Thumbprint -eq $tp | Select-Object -First 1
  if (-not $cert) { throw "certificate $tp not found in the CurrentUser/LocalMachine My store" }
} else {
  $cn = if ($Subject -match "CN=([^,]+)") { $Matches[1].Trim() } else { $Subject }
  # (no -CodeSigningCert switch: that dynamic provider parameter is not available in every PowerShell host)
  $cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object {
            $_.HasPrivateKey -and $_.NotAfter -gt (Get-Date) -and $_.Subject -like "CN=$cn*" -and
            ($_.EnhancedKeyUsageList | Where-Object { $_.ObjectId -eq "1.3.6.1.5.5.7.3.3" })
          } | Sort-Object NotAfter -Descending | Select-Object -First 1
  if (-not $cert) {
    "no code-signing certificate for '$cn': creating a self-signed one (3 years)"
    $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $Subject -KeyAlgorithm RSA -KeyLength 3072 `
            -HashAlgorithm SHA256 -KeyExportPolicy Exportable -CertStoreLocation Cert:\CurrentUser\My -NotAfter (Get-Date).AddYears(3)
  }
  $certDir = Join-Path $PSScriptRoot "cert"
  if (-not (Test-Path $certDir)) { New-Item -ItemType Directory -Path $certDir | Out-Null }
  $cer = Join-Path $certDir "autodj-codesign.cer"
  Export-Certificate -Cert $cert -FilePath $cer | Out-Null
  foreach ($store in "Root", "TrustedPublisher") {  # trust it on THIS machine so the signature validates here
    if (-not (Test-Path "Cert:\CurrentUser\$store\$($cert.Thumbprint)")) {
      Import-Certificate -FilePath $cer -CertStoreLocation "Cert:\CurrentUser\$store" | Out-Null
      "trusted on this PC: $store"
    }
  }
  "public cert for other PCs: $cer"
}
"signing with: $($cert.Subject)  [$($cert.Thumbprint)]"
$sig = $null
foreach ($ts in "http://timestamp.digicert.com", "http://timestamp.sectigo.com", "http://timestamp.globalsign.com/tsa/r6advanced1") {
  try { $sig = Set-AuthenticodeSignature -FilePath $exe -Certificate $cert -HashAlgorithm SHA256 -TimestampServer $ts; if ($sig.SignerCertificate) { break } }
  catch { "timestamp server $ts failed: $($_.Exception.Message)" }
}
if (-not $sig -or -not $sig.SignerCertificate) { throw "signing failed (is the file open in another program? offline?)" }

# ---------- 3. verify -------------------------------------------------------------------------------
Step "result"
$v = Get-AuthenticodeSignature $exe
"file:      $((Resolve-Path $exe).Path)  ($([math]::Round((Get-Item $exe).Length / 1MB, 1)) MB)"
"signature: $($v.Status)  $($v.StatusMessage)"
"signer:    $($v.SignerCertificate.Subject)"
"timestamp: $($v.TimeStamperCertificate.Subject)"
"sha256:    $((Get-FileHash $exe -Algorithm SHA256).Hash)"
if ($v.Status -ne "Valid") { Write-Warning "not 'Valid': expected for a self-signed cert on a PC that has not imported autodj-codesign.cer" }
