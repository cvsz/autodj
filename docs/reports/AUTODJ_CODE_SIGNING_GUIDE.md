# AutoDJ Code Signing Guide

**Repository:** `cvsz/autodj`  
**Build Script:** `build.ps1`  
**Installer Script:** `installer.nsi`  
**Release Workflow:** `.github/workflows/release.yml`  
**Date:** 2026-11-02  
**Status:** Integration complete; certificate required for release signing  

---

## 1. Overview

AutoDJ uses Authenticode code signing for Windows executables (`AutoDJ.exe`) and NSIS installers (`Camfrog-AutoDJ-Setup-*.exe`). Signing provides:

- **Identity assurance:** Users can verify the software was published by ZEAZDEV COMPANY LIMITED
- **Integrity protection:** Any tampering with the signed file invalidates the signature
- **SmartScreen reputation:** Signed executables from a recognized certificate authority avoid Windows Defender SmartScreen warnings
- **Timestamp validation:** Timestamps remain valid even after the certificate expires, as long as the timestamp was valid at signing time

## 2. Signing Integration Architecture

### 2.1 Build Script (`build.ps1`)

`build.ps1` implements the complete signing pipeline:

| Feature | Implementation |
|---------|---------------|
| Certificate input | `-Pfx` + `-Password` or `-Thumbprint` |
| Environment variables | `AUTODJ_PFX`, `AUTODJ_PFX_PASSWORD`, `AUTODJ_CERT_THUMBPRINT` |
| Self-signed fallback | `New-SelfSignedCertificate` with `CodeSigningCert` type (3-year validity) |
| EKU validation | Checks for Code Signing OID `1.3.6.1.5.5.7.3.3` |
| Expiration check | `NotAfter -gt (Get-Date)` |
| Private key check | `HasPrivateKey` |
| Timestamp servers | DigiCert → Sectigo → GlobalSign (fallback chain) |
| Hash algorithm | SHA256 |
| Verification | `Get-AuthenticodeSignature` after signing |
| Fail closed | Throws if signing fails or signature status is not valid |
| Unsigned builds | `-NoSign` switch for development/CI without certificate |

### 2.2 CI Integration (`.github/workflows/release.yml`)

The release workflow conditionally signs when certificate secrets are present:

| CI Secret | Purpose | build.ps1 Parameter |
|-----------|---------|---------------------|
| `AUTODJ_PFX` | Path to PFX certificate file | `-Pfx` |
| `AUTODJ_PFX_PASSWORD` | PFX password (secure string) | `-Password` |
| `AUTODJ_CERT_THUMBPRINT` | Thumbprint of cert in Windows store | `-Thumbprint` |

**Behavior:**
- If `AUTODJ_PFX` + `AUTODJ_PFX_PASSWORD` are set: sign with PFX
- Else if `AUTODJ_CERT_THUMBPRINT` is set: sign from certificate store
- Else: build with `-NoSign` (unsigned development build)
- No secrets are stored in the repository

### 2.3 NSIS Installer Signing

The NSIS installer (`installer.nsi`) is built by `makensis` in the release workflow. The installer itself is **not** Authenticode-signed by `makensis` (NSIS does not support embedded signing). The recommended approach is:

1. Build `AutoDJ.exe` and sign it with `build.ps1` (Authenticode)
2. Build the NSIS installer wrapping the signed `AutoDJ.exe`
3. Optionally sign the NSIS installer externally using `signtool.exe` with a code-signing certificate

## 3. Certificate Requirements

### 3.1 Certificate Type

| Requirement | Specification |
|-------------|---------------|
| Certificate purpose | Code Signing |
| EKU | `1.3.6.1.5.5.7.3.3` (Code Signing) |
| Key algorithm | RSA 2048-bit minimum (3072-bit recommended) |
| Hash algorithm | SHA256 |
| Validity period | 1–3 years |
| Private key | Exportable (for CI usage) or non-exportable (HSM) |
| Trust anchor | Public CA (DigiCert, Sectigo, GlobalSign, etc.) |

### 3.2 Certificate Acquisition

1. Purchase a code-signing certificate from a public CA (e.g., DigiCert, Sectigo, GlobalSign)
2. Complete identity validation (organization verification)
3. Receive PFX file or install into Windows certificate store
4. Export public `.cer` for distribution to users who need to trust the signer
5. Store PFX securely (encrypted, access-controlled, backed up)

### 3.3 Certificate Renewal

| Action | Timing | Procedure |
|--------|--------|-----------|
| Renew before expiry | 30 days before `NotAfter` | Purchase renewal from CA, install new cert, update CI secrets |
| Revoke on compromise | Immediately | Contact CA to revoke, publish revocation, rotate all secrets |
| Rotate secrets | Every 90 days | Regenerate PFX password, update `AUTODJ_PFX_PASSWORD` GitHub secret |

## 4. CI Secret Configuration

### 4.1 GitHub Secrets Configuration

Configure the following repository secrets in GitHub (Settings → Secrets and variables → Actions):

| Secret Name | Value Format | Example |
|-------------|--------------|---------|
| `AUTODJ_PFX` | Base64-encoded PFX file contents or file path accessible to the runner | `base64(cert.pfx)` |
| `AUTODJ_PFX_PASSWORD` | PFX file password (plain text, encrypted at rest by GitHub) | `CorrectHorseBatteryStaple42!` |
| `AUTODJ_CERT_THUMBPRINT` | 40-character hexadecimal certificate thumbprint | `A1B2C3D4E5F6...` |

### 4.2 Security Requirements

- **Never commit** PFX files, passwords, or private keys to the repository
- **Never log** secret values in CI output
- **Rotate** passwords and certificates on a regular schedule
- **Limit access** to secrets to authorized maintainers only
- **Audit** secret access through GitHub audit logs

## 5. Verification Procedures

### 5.1 Verify Signed Executable

```powershell
# Verify Authenticode signature
Get-AuthenticodeSignature -FilePath "dist\AutoDJ.exe"

# Expected output:
# Status: Valid
# SignerCertificate.Subject: CN=ZEAZDEV COMPANY LIMITED, ...
# StatusMessage: A certificate chain processed correctly, but terminated in a root
#                certificate which is not trusted by the trust provider.
#
# Note: "Not trusted by trust provider" is expected if the end-user has not
#       imported the CA root certificate. The signature itself is still valid.
```

### 5.2 Verify Certificate Chain

```powershell
# View certificate details
$cert = Get-PfxCertificate -FilePath "cert\autodj-codesign.pfx"
$cert.Subject
$cert.Thumbprint
$cert.NotAfter
$cert.EnhancedKeyUsageList | Where-Object { $_.ObjectId -eq "1.3.6.1.5.5.7.3.3" }
```

### 5.3 Verify Timestamp Validity

```powershell
$sig = Get-AuthenticodeSignature -FilePath "dist\AutoDJ.exe"
$sig.TimeStamperCertificate.Subject
$sig.TimeStamperCertificate.NotAfter
```

A valid timestamp means the signature remains verifiable even after the signing certificate expires.

## 6. Build Modes

| Build Type | Signing | Use Case | Distribution |
|------------|---------|----------|--------------|
| Development | `-NoSign` (unsigned) | Local testing, CI without certificate | Not for distribution |
| CI with secrets | PFX or Thumbprint (signed) | Automated release builds | Internal testing |
| Release | Real CA certificate (signed) | Public distribution | End users |

## 7. Fail-Closed Behavior

The build fails (throws an exception) when:

- Signing is requested but no certificate is available **and** `-NoSign` is not specified
- The signing operation fails (offline, timestamp server unreachable, etc.)
- The resulting signature status is not `Valid`
- The certificate lacks the Code Signing EKU
- The certificate has expired
- The certificate has no private key

This ensures that no unsigned executable is accidentally distributed as a release build.

## 8. Known Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Self-signed cert not trusted by default | Windows shows "Unknown publisher" warning | Import `cert\autodj-codesign.cer` into TrustedPublisher on each PC |
| NSIS installer not Authenticode-signed by makensis | Installer shows "Unknown publisher" | Sign externally with `signtool.exe` after build |
| Timestamp server dependency | Signing fails if all timestamp servers unreachable | Retry with alternative timestamp servers |
| PFX in CI secrets | Secret exposure if CI compromised | Use GitHub Environments with required reviewers |

## 9. Certificate Renewal Checklist

- [ ] Purchase renewal from CA before current certificate expires
- [ ] Install new certificate in secure location
- [ ] Update `AUTODJ_PFX` and `AUTODJ_PFX_PASSWORD` GitHub secrets
- [ ] Test signing with new certificate on a development build
- [ ] Export and distribute new public `.cer` to users
- [ ] Revoke old certificate only after new one is in use
- [ ] Document renewal date for next cycle

## 10. Blocker Status

**Status: BLOCKED — CERTIFICATE REQUIRED**

No code-signing certificate is currently configured in the repository or CI secrets. All release builds are produced unsigned (`-NoSign`). To enable signed releases:

1. Acquire a code-signing certificate from a public CA
2. Configure `AUTODJ_PFX` and `AUTODJ_PFX_PASSWORD` (or `AUTODJ_CERT_THUMBPRINT`) as GitHub repository secrets
3. Trigger a release workflow run to verify signing works end-to-end
4. Document the certificate fingerprint and expiration in this guide
