# Camfrog AutoDJ v0.2.6 — Security Audit & Supply Chain Verification

**Repository:** `cvsz/autodj`  
**Target Release:** `v0.2.6`  
**Release Commit SHA:** `e2ec1013859e587b41dcd047a234b0cf14cd7580`  
**Date:** 2026-11-01  
**Auditor:** ZEAZDEV Super Ultra AI ORC

---

## 1. Static Security & CI Scanning Status

All status checks on PR #54 and release commit `e2ec1013859e587b41dcd047a234b0cf14cd7580` completed with 0 errors:
- **CodeQL / Analyze GitHub Actions:** Passing cleanly.
- **Dependency Review:** Passing cleanly; zero critical or high vulnerabilities.
- **Repository Baseline Check:** Validated repository structure, YAML configurations, absence of tracked private secrets, and Markdown links.

---

## 2. Cryptographic Provenance & Sigstore Attestations

Four independent artifact attestations were created via GitHub Actions `actions/attest-build-provenance@v2` and signed via the Public Good Sigstore instance:
1. `AutoDJ.exe` (SHA-256: `8c4d0e1fc42267ac7055dea8f4451f59369692d4b58b1421c31bd6120bc8e1b0`)
2. `Camfrog-AutoDJ-Setup-0.2.6.exe` (SHA-256: `b5de87fc08d894064e7c95b608b889951ad34ac5998983d2358a3e2c6fbdf16c`)
3. `Camfrog-AutoDJ-v0.2.6.cdx.json` (SHA-256: `bd96226c33060ded3f2312a6e2d8926500d8c446d954c4352b560665c0cec85f`)
4. `SHA256SUMS.txt` (SHA-256: `94b40c6f9a58aaa619c43a55c4796901490bd374fcf75f887567b64af536ee3b`)

All attestations enforce SLSA Provenance v1 specifications and were independently validated using `gh attestation verify` with strict repository matching (`https://github.com/cvsz/autodj`).

---

## 3. SBOM Verification

The CycloneDX SBOM (`Camfrog-AutoDJ-v0.2.6.cdx.json`) was generated using specification version 1.6 and validated:
- Package: `camfrog-autodj` version `0.2.6`
- Total Components: 48 dependencies cataloged with complete license and package URL metadata.
- No unexpected transitive packages or unvetted scripts detected.
