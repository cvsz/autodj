# AutoDJ Authenticode Code Signing Setup

**Repository:** `cvsz/autodj`  
**Date:** 2026-11-02  

---

## 1. Overview

AutoDJ uses Authenticode code signing for Windows executables (`AutoDJ.exe`)
and NSIS installers (`Camfrog-AutoDJ-Setup-*.exe`). Signing provides identity
assurance, integrity protection, and SmartScreen reputation.

## 2. Certificate Requirements

| Requirement | Specification |
|-------------|---------------|
| Certificate purpose | Code Signing |
| EKU | `1.3.6.1.5.5.7.3.3` (Code Signing) |
| Key algorithm | RSA 2048-bit minimum (3072-bit recommended) |
| Hash algorithm | SHA256 |
| Validity period | 1–3 years |
| Trust anchor | Public CA (DigiCert, Sectigo, GlobalSign, etc.) |

## 3. Certificate Acquisition

1. Purchase a code-signing certificate from a public CA
2. Complete identity validation (organization verification)
3. Receive PFX file or install into Windows certificate store
4. Export public `.cer` for distribution to users

## 4. CI Secret Configuration

Configure the following repository secrets in GitHub
(Settings → Secrets and variables → Actions):

| Secret Name | Value Format | Example |
|-------------|--------------|---------|
| `AUTODJ_PFX` | Base64-encoded PFX or file path | Base64 string |
| `AUTODJ_PFX_PASSWORD` | PFX password | `***REDACTED***` |
| `AUTODJ_CERT_THUMBPRINT` | 40-char hex thumbprint | `A1B2C3D4E5F6...` |

**Never commit PFX files, passwords, or private keys to the repository.**

## 5. Local Signing

```powershell
# Sign with PFX file
.\build.ps1 -Pfx cert\autodj.pfx -Password "***REDACTED***"

# Sign with certificate from store
.\build.ps1 -Thumbprint A1B2C3D4E5F6...

# Unsigned development build
.\build.ps1 -NoSign
```

## 6. CI Signing

The release workflow (`.github/workflows/release.yml`) conditionally signs
when `AUTODJ_PFX`/`AUTODJ_PFX_PASSWORD` or `AUTODJ_CERT_THUMBPRINT` are set
as GitHub secrets. Without secrets, builds are unsigned (`-NoSign`).

## 7. Verification

```powershell
# Verify Authenticode signature
Get-AuthenticodeSignature -FilePath dist\AutoDJ.exe

# Verify with signtool
signtool verify /pa /v dist\AutoDJ.exe
signtool verify /pa /v Camfrog-AutoDJ-Setup-*.exe
```

## 8. Blocker Status

**No code-signing certificate is currently configured.** Release builds are
produced unsigned (`-NoSign`). A certificate from a public CA is required
before signed release artifacts can be produced.
