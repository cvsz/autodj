# AutoDJ Authenticode Code Signing Acceptance

**Repository:** `cvsz/autodj`  
**Base Commit SHA (`main`):** `6baa8b7fcc47544eb21e3430e9f9db0124df81c6`  
**Date:** 2026-11-02  
**Auditor:** ZEAZDEV Super Ultra AI ORC  
**Verification Status:** BLOCKED — CERTIFICATE REQUIRED  

---

## 1. Executive Summary

Authenticode code signing integration is fully implemented in `build.ps1` and wired into `.github/workflows/release.yml`. However, no code-signing certificate from a public CA is configured in the repository or CI secrets. All release builds are produced unsigned (`-NoSign`). No Authenticode validation can be performed without a valid certificate.

**This gate is BLOCKED — a code-signing certificate from a public CA is required before signed release artifacts can be produced or verified.**

---

## 2. Signing Integration Architecture

### 2.1 Build Script (`build.ps1`)

`build.ps1` implements a complete Authenticode signing pipeline:

| Feature | Implementation | File:Line |
|---------|---------------|-----------|
| Certificate input | `-Pfx` + `-Password` or `-Thumbprint` | build.ps1:18-20 |
| Environment variables | `AUTODJ_PFX`, `AUTODJ_PFX_PASSWORD`, `AUTODJ_CERT_THUMBPRINT` | build.ps1:18-20 |
| EKU validation | Checks for Code Signing OID `1.3.6.1.5.5.7.3.3` | build.ps1:124-125 |
| Expiration check | `NotAfter -gt (Get-Date)` | build.ps1:124 |
| Private key check | `HasPrivateKey` | build.ps1:123-124 |
| Timestamp servers | DigiCert → Sectigo → GlobalSign (fallback chain) | build.ps1:146-148 |
| Hash algorithm | SHA256 | build.ps1:147 |
| Signature verification | `Get-AuthenticodeSignature` after signing | build.ps1:154 |
| Fail closed | Throws if signing fails or status is not Valid | build.ps1:149-150 |
| Unsigned builds | `-NoSign` switch for development/CI | build.ps1:110 |

### 2.2 CI Integration (`.github/workflows/release.yml`)

The release workflow conditionally signs when certificate secrets are present:

| CI Secret | Purpose | build.ps1 Parameter |
|-----------|---------|---------------------|
| `AUTODJ_PFX` | Path to PFX certificate file | `-Pfx` |
| `AUTODJ_PFX_PASSWORD` | PFX password | `-Password` |
| `AUTODJ_CERT_THUMBPRINT` | Thumbprint of cert in Windows store | `-Thumbprint` |

**Behavior:**
- If `AUTODJ_PFX` + `AUTODJ_PFX_PASSWORD` are set: sign with PFX
- Else if `AUTODJ_CERT_THUMBPRINT` is set: sign from certificate store
- Else: build with `-NoSign` (unsigned development build)
- No secrets are stored in the repository

### 2.3 NSIS Installer Signing

NSIS (`makensis`) does not support embedded Authenticode signing. The recommended approach:

1. Build and sign `AutoDJ.exe` with `build.ps1` (Authenticode)
2. Build the NSIS installer wrapping the signed `AutoDJ.exe`
3. Optionally sign the NSIS installer externally using `signtool.exe`

### 2.4 Artifact Integrity

After signing, the release workflow:
1. Generates SHA256 checksums for all artifacts (`SHA256SUMS.txt`)
2. Generates CycloneDX SBOM (`cyclonedx-py environment`)
3. Attests build provenance (`actions/attest-build-provenance@v2`)
4. Uploads artifacts with 90-day retention

---

## 3. Validation Procedures (Not Executable Without Certificate)

| Validation | Command | Status |
|------------|---------|--------|
| Verify Authenticode signature | `Get-AuthenticodeSignature -FilePath "dist\AutoDJ.exe"` | BLOCKED |
| Verify with signtool | `signtool verify /pa /v dist\AutoDJ.exe` | BLOCKED |
| Certificate chain & EKU | `Get-PfxCertificate` + check EKU OID | BLOCKED |
| Timestamp verification | Check `TimeStamperCertificate` | BLOCKED |
| SHA256 verification | `Get-FileHash` vs `SHA256SUMS.txt` | BLOCKED |
| Provenance attestation | `gh attestation verify` | BLOCKED |

---

## 4. Certificate Requirements

| Requirement | Specification |
|-------------|---------------|
| Certificate purpose | Code Signing |
| EKU | `1.3.6.1.5.5.7.3.3` |
| Key algorithm | RSA 2048-bit minimum (3072-bit recommended) |
| Hash algorithm | SHA256 |
| Validity period | 1–3 years |
| Trust anchor | Public CA (DigiCert, Sectigo, GlobalSign, etc.) |

---

## 5. Blocker Status

**Status: BLOCKED — CERTIFICATE REQUIRED**

No code-signing certificate exists in the repository or CI secrets. All release builds are produced unsigned (`-NoSign`).

---

## 6. Required Actions

1. Acquire a code-signing certificate from a public CA
2. Configure `AUTODJ_PFX`/`AUTODJ_PFX_PASSWORD` or `AUTODJ_CERT_THUMBPRINT` as GitHub secrets
3. Trigger a release workflow run to verify signing end-to-end
4. Validate signed artifacts with `Get-AuthenticodeSignature` and `signtool verify`
