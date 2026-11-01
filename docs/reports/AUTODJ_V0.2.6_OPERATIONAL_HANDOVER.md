# Camfrog AutoDJ v0.2.6 — Operational Handover & Deployment Guide

**Repository:** `cvsz/autodj`  
**Official Release Target:** `v0.2.6`  
**Release Commit SHA:** `e2ec1013859e587b41dcd047a234b0cf14cd7580`  
**Tag:** `v0.2.6`  
**Release URL:** [https://github.com/cvsz/autodj/releases/tag/v0.2.6](https://github.com/cvsz/autodj/releases/tag/v0.2.6)  
**Date:** 2026-11-01  
**Classification:** `RELEASE_ACCEPTED`

---

## 1. Executive Summary

This Operational Handover document provides complete engineering, release, security, governance, and operational instructions for **Camfrog AutoDJ v0.2.6**.

All functional features, audio processing upgrades, bot moderation controls, Windows Hi-DPI GUI enhancements, packaging automation, supply-chain attestations, and documentation have been tested, approved by independent reviewer `policedbc`, merged by administrator `cvsz`, built on a clean Windows runner, and published to GitHub Releases.

---

## 2. Release & Repository Traceability

- **Repository Full Name:** `cvsz/autodj`
- **Default Branch:** `main`
- **Release Source Commit:** `e2ec1013859e587b41dcd047a234b0cf14cd7580`
- **Release Tag:** `v0.2.6` (annotated tag object `239eb206084554a13b8215e684f5db91e43e4689`)
- **Release URL:** [https://github.com/cvsz/autodj/releases/tag/v0.2.6](https://github.com/cvsz/autodj/releases/tag/v0.2.6)
- **Workflow Run ID:** `41289389204`
- **Persistent Artifact Archive:** `autodj-release-v0.2.6` (Artifact ID `13076458038`, 57.6 MB)

---

## 3. Governance Evidence

- **PR #54 (`chore: release Camfrog AutoDJ v0.2.6`):**
  - Peer Review Approval: `policedbc`
  - Merge Authority: `cvsz` (Squash merge at `e2ec101`)
  - CI Checks: 12/12 successful (`tests` Ubuntu/Windows Python 3.11/3.12, CodeQL, Dependency Review, Repository Baseline)
- **Ruleset Compliance:** No branch protection rules or push policies bypassed.

---

## 4. Release Assets & Cryptographic Manifest

| Asset Name | Size | SHA-256 Digest | Sigstore Attestation Verification |
|---|---|---|---|
| `AutoDJ.exe` | 29,192,022 B | `8c4d0e1fc42267ac7055dea8f4451f59369692d4b58b1421c31bd6120bc8e1b0` | `PASSED` (`gh attestation verify`) |
| `Camfrog-AutoDJ-Setup-0.2.6.exe` | 29,338,925 B | `b5de87fc08d894064e7c95b608b889951ad34ac5998983d2358a3e2c6fbdf16c` | `PASSED` (`gh attestation verify`) |
| `Camfrog-AutoDJ-v0.2.6.cdx.json` | 60,832 B | `bd96226c33060ded3f2312a6e2d8926500d8c446d954c4352b560665c0cec85f` | `PASSED` (`gh attestation verify`) |
| `SHA256SUMS.txt` | 274 B | `94b40c6f9a58aaa619c43a55c4796901490bd374fcf75f887567b64af536ee3b` | `PASSED` (`gh attestation verify`) |

---

## 5. Deployment & Installation Guide

### 5.1 Fresh Installation (Windows 11 / Windows 10)
1. Download `Camfrog-AutoDJ-Setup-0.2.6.exe` and `SHA256SUMS.txt` from the release page.
2. Verify checksum:
   ```powershell
   (Get-FileHash Camfrog-AutoDJ-Setup-0.2.6.exe -Algorithm SHA256).Hash
   ```
3. Run the installer:
   ```cmd
   Camfrog-AutoDJ-Setup-0.2.6.exe
   ```
4. Follow the setup wizard to complete installation. Desktop and Start Menu shortcuts will be created.

### 5.2 Standalone Portable Execution
1. Download `AutoDJ.exe`.
2. Ensure `mpv` and audio routing are present on your system.
3. Launch `AutoDJ.exe` directly or run diagnostics:
   ```cmd
   AutoDJ.exe --check
   ```

### 5.3 Upgrading from v0.2.4 / Previous Versions
1. Close any running instance of AutoDJ.
2. Run `Camfrog-AutoDJ-Setup-0.2.6.exe`.
3. The NSIS installer will detect existing installation directories, preserve `config.toml`, playlists, and logs, and update the application binaries cleanly.

---

## 6. Rollback & Recovery Instructions

In the unlikely event of runtime rollback:
1. Re-run `Camfrog-AutoDJ-Setup-0.2.4.exe` to restore v0.2.4 binaries.
2. Existing `config.toml` and `playlist.json` files are backward compatible.
3. Repository git history remains strictly immutable; v0.2.6 tag and releases can be audited at any time.

---

## 7. Final Handover Classification

```
================================================================================
FINAL CLASSIFICATION: RELEASE_ACCEPTED
================================================================================
```
All delivery requirements, release publication gates, and operational handovers are 100% complete.
