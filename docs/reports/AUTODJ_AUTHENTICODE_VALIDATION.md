# AutoDJ Authenticode Code Signing Validation

**Repository:** `cvsz/autodj`  
**Base Commit SHA (`main`):** `a837e0b70d48b4c28f0b209373e92f1bdd2592fe`  
**Date:** 2026-11-02  
**Auditor:** ZEAZDEV Super Ultra AI ORC  
**Verification Status:** BLOCKED — CERTIFICATE REQUIRED  

---

## 1. Executive Summary

Authenticode code signing integration is implemented in `build.ps1` and wired into `.github/workflows/release.yml`. However, no code-signing certificate is configured in the repository or CI secrets. All release builds are produced unsigned (`-NoSign`). No Authenticode validation can be performed without a valid certificate.

**This gate is BLOCKED — a code-signing certificate from a public CA is required before signed release artifacts can be produced or verified.**

---

## 2. Signing Integration Architecture

### 2.1 Build Script (`build.ps1`)

`build.ps1` implements a complete Authenticode signing pipeline:

| Feature | Implementation |
|---------|---------------|
| Certificate input | `-Pfx` + `-Password` or `-Thumbprint` |
| Environment variables | `AUTODJ_PFX`, `AUTODJ_PFX_PASSWORD`, `AUTODJ_CERT_THUMBPRINT` |
| EKU validation | Checks for Code Signing OID `1.3.6.1.5.5.7.3.3` |
| Expiration check | `NotAfter -gt (Get-Date)` |
| Private key check | `HasPrivateKey` |
| Timestamp servers | DigiCert → Sectigo → GlobalSign (fallback chain) |
| Hash algorithm | SHA256 |
| Signature verification | `Get-AuthenticodeSignature` after signing |
| Fail closed | Throws if signing fails or signature status is not valid |
| Unsigned builds | `-NoSign` switch for development/CI without certificate |

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

The NSIS installer (`installer.nsi`) is built by `makensis` in the release workflow. NSIS does not support embedded Authenticode signing via `makensis`. The recommended approach:

1. Build and sign `AutoDJ.exe` with `build.ps1` (Authenticode)
2. Build the NSIS installer wrapping the signed `AutoDJ.exe`
3. Optionally sign the NSIS installer externally using `signtool.exe` with a code-signing certificate

### 2.4 Artifact Integrity

After signing, the release workflow:
1. Generates SHA256 checksums for all artifacts (`SHA256SUMS.txt`)
2. Generates CycloneDX SBOM (`cyclonedx-py`)
3. Attests build provenance (`actions/attest-build-provenance@v2`)
4. Uploads artifacts with 90-day retention

**Note:** Checksums are generated after signing, so they cover the final signed artifacts.

---

## 3. Validation Procedures (Not Executable Without Certificate)

### 3.1 Verify Signed Executable

```powershell
Get-AuthenticodeSignature -FilePath "dist\AutoDJ.exe"
```

Expected: `Status: Valid`, signer certificate with Code Signing EKU.

### 3.2 Verify with signtool

```cmd
signtool verify /pa /v dist\AutoDJ.exe
signtool verify /pa /v Camfrog-AutoDJ-Setup-*.exe
```

### 3.3 Certificate Chain Verification

```powershell
$cert = Get-PfxCertificate -FilePath "cert\autodj-codesign.pfx"
$cert.EnhancedKeyUsageList | Where-Object { $_.ObjectId -eq "1.3.6.1.5.5.7.3.3" }
```

### 3.4 Timestamp Verification

```powershell
$sig = Get-AuthenticodeSignature -FilePath "dist\AutoDJ.exe"
$sig.TimeStamperCertificate.Subject
$sig.TimeStamperCertificate.NotAfter
```

### 3.5 SHA256 Verification

```powershell
Get-FileHash dist\AutoDJ.exe -Algorithm SHA256
# Compare against SHA256SUMS.txt
```

---

## 4. Certificate Requirements

| Requirement | Specification |
|-------------|---------------|
| Certificate purpose | Code Signing |
| EKU | `1.3.6.1.5.5.7.3.3` (Code Signing) |
| Key algorithm | RSA 2048-bit minimum (3072-bit recommended) |
| Hash algorithm | SHA256 |
| Validity period | 1–3 years |
| Private key | Exportable (for CI) or non-exportable (HSM) |
| Trust anchor | Public CA (DigiCert, Sectigo, GlobalSign, etc.) |

---

## 5. Blocker Status

**Status: BLOCKED — CERTIFICATE REQUIRED**

No code-signing certificate exists in the repository or CI secrets. The following cannot be completed:

| Validation | Reason |
|------------|--------|
| `Get-AuthenticodeSignature` on release artifacts | No signed artifacts exist |
| `signtool verify` | No signed artifacts exist |
| Certificate chain verification | No certificate available |
| Timestamp verification | No signed artifacts exist |
| SHA256 verification of signed artifacts | No signed artifacts exist |
| Provenance attestation verification | No signed artifacts exist |

---

## 6. Required Actions

1. Acquire a code-signing certificate from a public CA (DigiCert, Sectigo, GlobalSign, etc.)
2. Configure `AUTODJ_PFX` and `AUTODJ_PFX_PASSWORD` (or `AUTODJ_CERT_THUMBPRINT`) as GitHub repository secrets
3. Trigger a release workflow run to verify signing works end-to-end
4. Validate the signed artifact with `Get-AuthenticodeSignature` and `signtool verify`
5. Document the certificate fingerprint and expiration

---

## 7. Residual Risk

Even with a certificate, the following residual risks remain:

| Risk | Mitigation |
|------|------------|
| Certificate compromise | Rotate certificate immediately, revoke via CA |
| Certificate expiration | Renew before `NotAfter`; timestamps remain valid after expiry |
| Timestamp server outage | Build fails closed (no signing without timestamp) |
| Private key exposure in CI | Use GitHub Environments with required reviewers; limit secret access |
