# Camfrog AutoDJ v0.2.6 — Independent Release & Supply-Chain Verification

**Repository:** `cvsz/autodj`  
**Release Tag:** `v0.2.6`  
**Peeled Commit SHA:** `e2ec1013859e587b41dcd047a234b0cf14cd7580`  
**Date:** 2026-11-01  
**Status:** `COMPLETED_VERIFIED`

---

## 1. Independent Artifact Verification

All four published assets from `https://github.com/cvsz/autodj/releases/tag/v0.2.6` were downloaded and independently verified:

| File Name | Size (Bytes) | SHA-256 Digest | Checksum Match | Sigstore Policy Verification |
|---|---|---|---|---|
| `AutoDJ.exe` | 29,192,022 | `8c4d0e1fc42267ac7055dea8f4451f59369692d4b58b1421c31bd6120bc8e1b0` | `OK` | `PASSED` (`cvsz/autodj` / `v0.2.6`) |
| `Camfrog-AutoDJ-Setup-0.2.6.exe` | 29,338,925 | `b5de87fc08d894064e7c95b608b889951ad34ac5998983d2358a3e2c6fbdf16c` | `OK` | `PASSED` (`cvsz/autodj` / `v0.2.6`) |
| `Camfrog-AutoDJ-v0.2.6.cdx.json` | 60,832 | `bd96226c33060ded3f2312a6e2d8926500d8c446d954c4352b560665c0cec85f` | `OK` | `PASSED` (`cvsz/autodj` / `v0.2.6`) |
| `SHA256SUMS.txt` | 274 | `94b40c6f9a58aaa619c43a55c4796901490bd374fcf75f887567b64af536ee3b` | `OK` | `PASSED` (`cvsz/autodj` / `v0.2.6`) |

---

## 2. Cryptographic Attestation Verification

Executed via GitHub CLI with strict repository and provenance policy:
```bash
gh attestation verify AutoDJ.exe --repo cvsz/autodj
gh attestation verify Camfrog-AutoDJ-Setup-0.2.6.exe --repo cvsz/autodj
gh attestation verify Camfrog-AutoDJ-v0.2.6.cdx.json --repo cvsz/autodj
gh attestation verify SHA256SUMS.txt --repo cvsz/autodj
```
- **Predicate Type:** `https://slsa.dev/provenance/v1`
- **OIDC Issuer:** `https://token.actions.githubusercontent.com`
- **Transparency Log:** Public Good Sigstore Rekor instances verified.
- **Result:** All 4 attestations match repository criteria with 100% cryptographic integrity.

---

## 3. CycloneDX SBOM Structure Audit

- **Specification:** CycloneDX v1.6
- **Metadata Component:** `camfrog-autodj` version `0.2.6`
- **Total Components:** 48 dependencies cataloged with complete license IDs and purls.
- **Verification Result:** Conforms to CycloneDX JSON schema.
