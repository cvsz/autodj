<#  Sign dist\AutoDJ.exe (Authenticode, SHA256 + timestamp).
    Pick ONE certificate source:
      -Pfx C:\path\cert.pfx [-Password ...]   (or env AUTODJ_PFX / AUTODJ_PFX_PASSWORD)
      -Thumbprint <hex>                        (or env AUTODJ_CERT_THUMBPRINT; cert in CurrentUser\My / LocalMachine\My)
      (or defaults to auto-finding/creating self-signed cert and saving .cer to cert\autodj-codesign.cer)
    Optional: -File <exe>, -TimestampServer <url> #>
param(
  [string]$File = "dist\AutoDJ.exe",
  [string]$Pfx = $env:AUTODJ_PFX,
  [string]$Password = $env:AUTODJ_PFX_PASSWORD,
  [string]$Thumbprint = $env:AUTODJ_CERT_THUMBPRINT,
  [string]$Subject = "CN=ZEAZDEV COMPANY LIMITED, O=ZEAZDEV COMPANY LIMITED, C=TH",
  [string]$TimestampServer = "http://timestamp.digicert.com"
)
$ErrorActionPreference = "Stop"
if ($PSVersionTable.PSVersion.Major -le 5) {
  # Same as in build.ps1: keep PS 5.1 from resolving PS7 module dirs so the Certificate provider (Cert:) loads.
  $env:PSModulePath = ($env:PSModulePath -split ';' | Where-Object {
    $_ -and $_ -notmatch 'PowerShell[\\/]7[\\/]Modules' -and
    $_ -notmatch 'Documents[\\/]PowerShell[\\/]Modules' -and
    $_ -notmatch 'Program Files[\\/]PowerShell[\\/]Modules'
  }) -join ';'
}
if (-not (Test-Path $File)) { throw "not found: $File (build first)" }
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
  $cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object {
            $_.HasPrivateKey -and $_.NotAfter -gt (Get-Date) -and $_.Subject -like "CN=$cn*" -and
            ($_.EnhancedKeyUsageList | Where-Object { $_.ObjectId -eq "1.3.6.1.5.5.7.3.3" })
          } | Sort-Object NotAfter -Descending | Select-Object -First 1
  if (-not $cert) {
    "no code-signing certificate for '$cn': creating a self-signed one (3 years)"
    $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $Subject -KeyAlgorithm RSA -KeyLength 3072 `
            -HashAlgorithm SHA256 -KeyExportPolicy Exportable -CertStoreLocation Cert:\CurrentUser\My -NotAfter (Get-Date).AddYears(3)
  }
  $certDir = Join-Path $PSScriptRoot "..\cert"
  if (-not (Test-Path $certDir)) { New-Item -ItemType Directory -Path $certDir | Out-Null }
  $cer = Join-Path (Resolve-Path $certDir) "autodj-codesign.cer"
  Export-Certificate -Cert $cert -FilePath $cer | Out-Null
  foreach ($store in "Root", "TrustedPublisher") {
    if (-not (Test-Path "Cert:\CurrentUser\$store\$($cert.Thumbprint)")) {
      Import-Certificate -FilePath $cer -CertStoreLocation "Cert:\CurrentUser\$store" | Out-Null
      "trusted on this PC: $store"
    }
  }
  "public cert for other PCs: $cer"
}
"signing with: $($cert.Subject)  [$($cert.Thumbprint)]"
$sig = $null
foreach ($ts in $TimestampServer, "http://timestamp.sectigo.com", "http://timestamp.globalsign.com/tsa/r6advanced1") {
  try { $sig = Set-AuthenticodeSignature -FilePath $File -Certificate $cert -HashAlgorithm SHA256 -TimestampServer $ts; if ($sig.SignerCertificate) { break } }
  catch { "timestamp server $ts failed: $($_.Exception.Message)" }
}
if (-not $sig -or -not $sig.SignerCertificate) { throw "signing failed (is the file open in another program? offline?)" }
"{0}: {1} ({2})" -f $File, $sig.Status, $sig.StatusMessage
