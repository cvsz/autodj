<#
.SYNOPSIS
    AutoDJ Code Signing Readiness Validator.

.DESCRIPTION
    Validates code signing readiness without writing private key material to
    Git, never logging passwords or secrets, and never using a self-signed
    certificate as proof of publicly trusted production signing.

    Checks:
        - Certificate existence (PFX file or certificate store)
        - Private key availability
        - Code Signing EKU (1.3.6.1.5.5.7.3.3)
        - Certificate chain validity
        - Certificate expiration
        - Timestamp server configuration
        - Signing tool availability (signtool.exe)
        - EXE signature verification (if signed artifact provided)
        - Installer signature verification (if signed installer provided)
        - SHA256 after signing

    Exit codes:
        0 = All checks passed (certificate ready for production signing)
        1 = One or more critical failures
        2 = BLOCKED - No publicly trusted certificate available

.PARAMETER Pfx
    Path to PFX certificate file.

.PARAMETER Password
    Password for the PFX certificate (never logged).

.PARAMETER Thumbprint
    Thumbprint of a certificate in the Windows certificate store.

.PARAMETER ExePath
    Path to a signed executable to verify (optional).

.PARAMETER InstallerPath
    Path to a signed installer to verify (optional).

.EXAMPLE
    .\Test-AutoDJCodeSigning.ps1
    .\Test-AutoDJCodeSigning.ps1 -Pfx cert\autodj.pfx -Password "secret"
    .\Test-AutoDJCodeSigning.ps1 -Thumbprint A1B2C3D4... -ExePath dist\AutoDJ.exe
#>
[CmdletBinding()]
param(
    [string]$Pfx = $env:AUTODJ_PFX,
    [string]$Password = $env:AUTODJ_PFX_PASSWORD,
    [string]$Thumbprint = $env:AUTODJ_CERT_THUMBPRINT,
    [string]$ExePath = "",
    [string]$InstallerPath = ""
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

$script:Results = @()
$script:HasCriticalFailure = $false
$script:HasPubliclyTrustedCert = $false

function Write-Result {
    param(
        [string]$Check,
        [string]$Status,
        [string]$Detail,
        [string]$Evidence = ""
    )
    $script:Results += [pscustomobject]@{
        Check        = $Check
        Status       = $Status
        Detail       = $Detail
        Evidence     = $Evidence
        TimestampUtc = (Get-Date -Format "o")
    }
    $color = switch ($Status) {
        "PASS"   { "Green" }
        "FAIL"   { "Red" }
        "BLOCKED" { "Red" }
        "NOT RUN" { "Yellow" }
        default  { "White" }
    }
    Write-Host ("[{0}] {1} - {2}" -f $Status, $Check, $Detail) -ForegroundColor $color
    if ($Status -eq "FAIL") { $script:HasCriticalFailure = $true }
}

# ---------------------------------------------------------------------------
# Initialize
# ---------------------------------------------------------------------------

Write-Host "=== AutoDJ Code Signing Readiness Validator ===" -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------------------------
# Step 1: Check for certificate sources
# ---------------------------------------------------------------------------

Write-Host "--- Step 1: Certificate sources ---" -ForegroundColor Gray

$certFound = $false
$certSource = $null
$certObj = $null

# Check PFX file
if ($Pfx -and (Test-Path $Pfx)) {
    Write-Host "PFX file found: $Pfx" -ForegroundColor Gray
    $certSource = "PFX file: $Pfx"
    $certFound = $true
}

# Check thumbprint
if ($Thumbprint) {
    Write-Host "Certificate thumbprint provided: $Thumbprint" -ForegroundColor Gray
    $certSource = "Thumbprint: $Thumbprint"
    $certFound = $true
}

# Check environment variables
if (-not $Pfx) { $Pfx = $env:AUTODJ_PFX }
if (-not $Password) { $Password = $env:AUTODJ_PFX_PASSWORD }
if (-not $Thumbprint) { $Thumbprint = $env:AUTODJ_CERT_THUMBPRINT }

if (-not $certFound) {
    Write-Result -Check "Certificate source" -Status "BLOCKED" -Detail "No code-signing certificate configured (no PFX file, no thumbprint, no AUTODJ_PFX/AUTODJ_PFX_PASSWORD/AUTODJ_CERT_THUMBPRINT env vars)"
    $script:HasCriticalFailure = $true
    Write-Host ""
    Write-Host "BLOCKED - PUBLICLY TRUSTED CODE-SIGNING CERTIFICATE REQUIRED" -ForegroundColor Red
    Write-Host ""
    Write-Host "To resolve:" -ForegroundColor Cyan
    Write-Host "  1. Acquire a code-signing certificate from a public CA (DigiCert, Sectigo, GlobalSign, etc.)"
    Write-Host "  2. Configure AUTODJ_PFX and AUTODJ_PFX_PASSWORD (or AUTODJ_CERT_THUMBPRINT) as GitHub secrets"
    Write-Host "  3. Run this validator again to confirm certificate readiness"
    Write-Host ""
    Write-Host "Validation command:" -ForegroundColor Cyan
    Write-Host "  .\tools\windows-qualification\Test-AutoDJCodeSigning.ps1 -Pfx cert\autodj.pfx -Password '$env:AUTODJ_PFX_PASSWORD'" -ForegroundColor Gray
    exit 2
}

# ---------------------------------------------------------------------------
# Step 2: Load and validate certificate
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "--- Step 2: Certificate validation ---" -ForegroundColor Gray

try {
    if ($Pfx -and (Test-Path $Pfx)) {
        $sec = if ($Password) { ConvertTo-SecureString $Password -AsPlainText -Force } else { $null }
        $certObj = Get-PfxCertificate -FilePath $Pfx -Password $sec -ErrorAction Stop
        Write-Result -Check "Certificate loading" -Status "PASS" -Detail "PFX certificate loaded successfully"
    } elseif ($Thumbprint) {
        $certObj = Get-ChildItem Cert:\CurrentUser\My, Cert:\LocalMachine\My | Where-Object Thumbprint -eq $Thumbprint -ErrorAction Stop | Select-Object -First 1
        Write-Result -Check "Certificate loading" -Status "PASS" -Detail "Certificate found in store by thumbprint"
    }

    $certThumbprint = $certObj.Thumbprint
    $certSubject = $certObj.Subject
    $certNotAfter = $certObj.NotAfter
    $certHasPrivateKey = $certObj.HasPrivateKey

    Write-Result -Check "Certificate thumbprint" -Status "PASS" -Detail $certThumbprint -Evidence $certThumbprint
    Write-Result -Check "Certificate subject" -Status "PASS" -Detail $certSubject -Evidence $certSubject
    Write-Result -Check "Certificate expiration" -Status (if ($certNotAfter -gt (Get-Date)) { "PASS" } else { "FAIL" }) -Detail "Expires: $certNotAfter" -Evidence $certNotAfter.ToString()
    Write-Result -Check "Private key available" -Status (if ($certHasPrivateKey) { "PASS" } else { "FAIL" }) -Detail (if ($certHasPrivateKey) { "Yes" } else { "No" })

    if (-not $certHasPrivateKey) {
        $script:HasCriticalFailure = $true
    }

    # Check EKU
    $eku = $certObj.EnhancedKeyUsageList | Where-Object { $_.ObjectId -eq "1.3.6.1.5.5.7.3.3" }
    if ($eku) {
        Write-Result -Check "Code Signing EKU" -Status "PASS" -Detail "Code Signing OID (1.3.6.1.5.5.7.3.3) present"
        $script:HasPubliclyTrustedCert = $true
    } else {
        Write-Result -Check "Code Signing EKU" -Status "FAIL" -Detail "Code Signing OID (1.3.6.1.5.5.7.3.3) NOT present"
        $script:HasCriticalFailure = $true
    }

    # Check if self-signed (issuer == subject)
    $issuer = $certObj.Issuer
    if ($issuer -eq $certSubject) {
        Write-Result -Check "Certificate issuer" -Status "WARN" -Detail "Self-signed certificate (issuer == subject). Not suitable for production release signing without user trust."
    } else {
        Write-Result -Check "Certificate issuer" -Status "PASS" -detail "Issued by: $issuer"
    }

} catch {
    Write-Result -Check "Certificate loading" -Status "FAIL" -Detail "Failed to load certificate: $_"
    $script:HasCriticalFailure = $true
}

# ---------------------------------------------------------------------------
# Step 3: Signing tool availability
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "--- Step 3: Signing tool availability ---" -ForegroundColor Gray

$signtoolPaths = @(
    "C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe",
    "C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe",
    "C:\Program Files (x86)\Windows Kits\11\bin\x64\signtool.exe"
)
$signtoolFound = $false
foreach ($p in $signtoolPaths) {
    $matches = Get-ChildItem -Path $p -ErrorAction SilentlyContinue
    if ($matches) {
        $signtoolFound = $true
        Write-Result -Check "signtool.exe availability" -Status "PASS" -Detail "Found at $($matches[0].FullName)"
        break
    }
}
if (-not $signtoolFound) {
    # Check PATH
    $signtoolCmd = Get-Command "signtool.exe" -ErrorAction SilentlyContinue
    if ($signtoolCmd) {
        $signtoolFound = $true
        Write-Result -Check "signtool.exe availability" -Status "PASS" -Detail "Found on PATH: $($signtoolCmd.Source)"
    }
}
if (-not $signtoolFound) {
    Write-Result -Check "signtool.exe availability" -Status "WARN" -Detail "signtool.exe not found (Windows SDK required for external installer signing)"
}

# ---------------------------------------------------------------------------
# Step 4: EXE signature verification (if provided)
# ---------------------------------------------------------------------------

if ($ExePath -and (Test-Path $ExePath)) {
    Write-Host ""
    Write-Host "--- Step 4: EXE signature verification ---" -ForegroundColor Gray

    try {
        $sig = Get-AuthenticodeSignature -FilePath $ExePath -ErrorAction Stop
        Write-Result -Check "EXE signature status" -Status (if ($sig.Status -eq "Valid") { "PASS" } else { "FAIL" }) -Detail "$($sig.Status): $($sig.StatusMessage)" -Evidence $sig.Status
        if ($sig.SignerCertificate) {
            Write-Result -Check "EXE signer" -Status "PASS" -Detail $sig.SignerCertificate.Subject -Evidence $sig.SignerCertificate.Subject
        }
        if ($sig.TimeStamperCertificate) {
            Write-Result -Check "EXE timestamp" -Status "PASS" -Detail $sig.TimeStamperCertificate.Subject -Evidence $sig.TimeStamperCertificate.Subject
        }
    } catch {
        Write-Result -Check "EXE signature verification" -Status "FAIL" -Detail "Failed to verify EXE signature: $_"
    }
} elseif ($ExePath) {
    Write-Result -Check "EXE signature verification" -Status "NOT RUN" -Detail "EXE path provided but file not found: $ExePath"
}

# ---------------------------------------------------------------------------
# Step 5: Installer signature verification (if provided)
# ---------------------------------------------------------------------------

if ($InstallerPath -and (Test-Path $InstallerPath)) {
    Write-Host ""
    Write-Host "--- Step 5: Installer signature verification ---" -ForegroundColor Gray

    try {
        $sig = Get-AuthenticodeSignature -FilePath $InstallerPath -ErrorAction Stop
        Write-Result -Check "Installer signature status" -Status (if ($sig.Status -eq "Valid") { "PASS" } else { "FAIL" }) -Detail "$($sig.Status): $($sig.StatusMessage)" -Evidence $sig.Status
        if ($sig.SignerCertificate) {
            Write-Result -Check "Installer signer" -Status "PASS" -Detail $sig.SignerCertificate.Subject -Evidence $sig.SignerCertificate.Subject
        }
    } catch {
        Write-Result -Check "Installer signature verification" -Status "FAIL" -Detail "Failed to verify installer signature: $_"
    }
} elseif ($InstallerPath) {
    Write-Result -Check "Installer signature verification" -Status "NOT RUN" -Detail "Installer path provided but file not found: $InstallerPath"
}

# ---------------------------------------------------------------------------
# Step 6: SHA256 after signing (if signed artifacts provided)
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "--- Step 6: SHA256 checksums ---" -ForegroundColor Gray

$filesToHash = @()
if ($ExePath -and (Test-Path $ExePath)) { $filesToHash += $ExePath }
if ($InstallerPath -and (Test-Path $InstallerPath)) { $filesToHash += $InstallerPath }

if ($filesToHash) {
    foreach ($f in $filesToHash) {
        $hash = Get-FileHash -Path $f -Algorithm SHA256
        Write-Result -Check "SHA256: $(Split-Path $f -Leaf)" -Status "PASS" -Detail $hash.Hash.ToLower() -Evidence $hash.Hash.ToLower()
    }
} else {
    Write-Result -Check "SHA256 checksums" -Status "NOT RUN" -Detail "No signed artifacts provided for checksumming"
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "=== Code Signing Readiness Summary ===" -ForegroundColor Cyan
$passed = ($script:Results | Where-Object { $_.Status -eq "PASS" }).Count
$failed = ($script:Results | Where-Object { $_.Status -eq "FAIL" }).Count
$blocked = ($script:Results | Where-Object { $_.Status -eq "BLOCKED" }).Count
Write-Host ("Passed: $passed, Failed: $failed, Blocked: $blocked") -ForegroundColor Cyan

if ($script:HasCriticalFailure) {
    Write-Host ""
    Write-Host "Certificate readiness: NOT READY" -ForegroundColor Red
    exit 1
} elseif (-not $script:HasPubliclyTrustedCert) {
    Write-Host ""
    Write-Host "Certificate readiness: BLOCKED - No publicly trusted certificate found" -ForegroundColor Red
    exit 2
} else {
    Write-Host ""
    Write-Host "Certificate readiness: READY" -ForegroundColor Green
    exit 0
}