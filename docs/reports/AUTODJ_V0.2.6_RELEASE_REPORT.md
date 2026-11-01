# Camfrog AutoDJ v0.2.6 — Official Release Report

**Repository:** `cvsz/autodj`  
**Official Release Target:** `v0.2.6`  
**Release Commit SHA:** `e2ec1013859e587b41dcd047a234b0cf14cd7580`  
**Workflow Run:** [#41289389204](https://github.com/cvsz/autodj/actions/runs/41289389204)  
**Release URL:** [https://github.com/cvsz/autodj/releases/tag/v0.2.6](https://github.com/cvsz/autodj/releases/tag/v0.2.6)  
**Date:** 2026-11-01  
**Status:** `RELEASE_ACCEPTED`

---

## 1. Executive Summary

Camfrog AutoDJ `v0.2.6` has been officially built, attested, and published. All required assets—including the Windows NSIS installer, standalone binary, CycloneDX Software Bill of Materials (SBOM), and SHA-256 manifest—are attached to the GitHub release, verified via independent downloads, and backed by cryptographically valid Sigstore build provenance attestations.

---

## 2. Release Artifact Inventory & Verification

| Asset | Size (Bytes) | SHA-256 Digest | Sigstore Attestation Policy Match |
|---|---|---|---|
| `AutoDJ.exe` | 29,192,022 | `8c4d0e1fc42267ac7055dea8f4451f59369692d4b58b1421c31bd6120bc8e1b0` | `PASSED` (`cvsz/autodj` / `v0.2.6`) |
| `Camfrog-AutoDJ-Setup-0.2.6.exe` | 29,338,925 | `b5de87fc08d894064e7c95b608b889951ad34ac5998983d2358a3e2c6fbdf16c` | `PASSED` (`cvsz/autodj` / `v0.2.6`) |
| `Camfrog-AutoDJ-v0.2.6.cdx.json` | 60,832 | `bd96226c33060ded3f2312a6e2d8926500d8c446d954c4352b560665c0cec85f` | `PASSED` (`cvsz/autodj` / `v0.2.6`) |
| `SHA256SUMS.txt` | 274 | `94b40c6f9a58aaa619c43a55c4796901490bd374fcf75f887567b64af536ee3b` | `PASSED` (`cvsz/autodj` / `v0.2.6`) |

---

## 3. Workflow & Retention

- **Workflow Name:** `Release` (`.github/workflows/release.yml`)
- **Run ID:** `41289389204`
- **Runner OS:** `windows-latest`
- **Python Version:** `3.11`
- **NSIS Version:** Modern UI 2
- **Persistent Artifact:** `autodj-release-v0.2.6` (57.6 MB zip, ID `13076458038`, 90-day retention).
