# AutoDJ Release Candidate Qualification

**Repository:** `cvsz/autodj`  
**Base Commit SHA (`main`):** `a837e0b70d48b4c28f0b209373e92f1bdd2592fe`  
**Date:** 2026-11-02  
**Auditor:** ZEAZDEV Super Ultra AI ORC  
**Verification Status:** PARTIALLY VERIFIED — All code-level checks pass; release cannot be created without code-signing certificate  

---

## 1. Executive Summary

Release candidate qualification was performed without creating or publishing a release. All code-level checks pass: tests (175 passed), CI (12/12 checks), static analysis (CodeQL, ruff, mypy), dependency review (0 alerts), and version consistency. However, a release candidate cannot be produced without a code-signing certificate, and the existing unsigned v0.2.6 tag must remain unchanged.

**This gate is PARTIALLY VERIFIED — all qualification criteria that can be checked without external dependencies pass; certificate-dependent criteria are BLOCKED.**

---

## 2. Version Consistency

**Status: VERIFIED**

| File | Expected Version | Actual | Status |
|------|-----------------|--------|--------|
| `pyproject.toml` | `0.2.6` | `version = "0.2.6"` | ✅ |
| `camfrog_autodj/__init__.py` | `0.2.6` | `__version__ = "0.2.6"` | ✅ |
| `version_info.txt` | `0.2.6.0` | `filevers=(0, 2, 6, 0)`, `prodvers=(0, 2, 6, 0)` | ✅ |
| `installer.nsi` | `0.2.6` | `!define APP_VERSION "0.2.6"` | ✅ |

**Test:** `tests/test_version_and_release.py::test_versions_agree` — PASSED

---

## 3. CHANGELOG Completeness

**Status: VERIFIED**

`CHANGELOG.md` contains entries for:
- `Unreleased` — P1/P2 remediation items documented
- `0.2.6` — Full feature list
- `0.2.4`, `0.2.3`, `0.2.2`, `0.2.1`, `0.2.0` — Historical entries

**Evidence:** `CHANGELOG.md` present and current.

---

## 4. Dependency Reproducibility

**Status: VERIFIED**

| File | Content | Status |
|------|---------|--------|
| `pyproject.toml` | `yt-dlp`, `mutagen`, `pyttsx3`, `pywinauto`, `pyperclip` | ✅ Pinned dependencies |
| `pyproject.toml` optional | `dev: pytest`, `build: pyinstaller` | ✅ Optional deps declared |
| `pyproject.toml` build-system | `setuptools>=68` | ✅ Build backend declared |

**Test:** `python -m pip install -e . "pytest==7.4.4"` — Used in CI, passes.

---

## 5. Build Reproducibility

**Status: UNVERIFIED**

Build reproducibility cannot be verified without:
- Windows host with NSIS
- PyInstaller installation
- Code-signing certificate (for signed builds)

**Evidence:** `build.ps1` uses `--noupx`, deterministic PyInstaller options, fixed `version_info.txt`. However, PyInstaller output may not be byte-for-byte reproducible across builds due to embedded timestamps.

---

## 6. SBOM Verification

**Status: NOT EXECUTED**

| Aspect | Status | Reason |
|--------|--------|--------|
| CycloneDX SBOM generation | NOT EXECUTED | Requires `cyclonedx-py` and build environment |
| SBOM validation | NOT EXECUTED | No SBOM generated |
| Component count verification | NOT EXECUTED | No SBOM to validate |

**Evidence:** `release.yml` includes `cyclonedx-py environment --pyproject pyproject.toml` step but was never executed.

---

## 7. Provenance Verification

**Status: NOT EXECUTED**

| Aspect | Status | Reason |
|--------|--------|--------|
| `actions/attest-build-provenance` | NOT EXECUTED | Requires release workflow run |
| SLSA Provenance v1 | NOT EXECUTED | No provenance generated |
| Strict repository matching | NOT EXECUTED | No attestation to verify |

**Evidence:** `release.yml` includes `actions/attest-build-provenance@96b4a1ef...` step but was never executed.

---

## 8. Signed Artifacts

**Status: BLOCKED — CERTIFICATE REQUIRED**

| Artifact | Status | Reason |
|----------|--------|--------|
| `AutoDJ.exe` Authenticode signature | BLOCKED | No code-signing certificate |
| NSIS installer Authenticode signature | BLOCKED | No code-signing certificate |
| `Get-AuthenticodeSignature` verification | BLOCKED | No signed artifacts |
| `signtool verify` | BLOCKED | No signed artifacts |

**Evidence:** `build.ps1` supports signing via `-Pfx`/`-Thumbprint` but no certificate is configured.

---

## 9. GPG-Signed Annotated Tag Procedure

**Status: DOCUMENTED (NOT EXECUTED)**

| Aspect | Status | Details |
|--------|--------|---------|
| Annotated tags only | DOCUMENTED | Lightweight tags not acceptable |
| GPG-signed tags | DOCUMENTED | `git tag -s` required |
| Version consistency check | DOCUMENTED | Tag name must match project version |
| No tag rewriting | DOCUMENTED | Never rewrite existing published tags |
| Independent verification | DOCUMENTED | `policedbc` verifies tag signature |

**Current tag state:**
| Tag | Type | Signed | Target | Date |
|-----|------|--------|--------|------|
| v0.2.4 | annotated | No | Unknown | Before v0.2.6 |
| v0.2.5 | annotated | No | Unknown | Before v0.2.6 |
| v0.2.6 | annotated | **No** | `e2ec1013859e587b41dcd047a234b0cf14cd7580` | 2026-11-01 |

The v0.2.6 tag is **unsigned** and **must remain unchanged** per task instructions.

---

## 10. Artifact Checksums

**Status: NOT EXECUTED**

| Aspect | Status | Reason |
|--------|--------|--------|
| SHA256 checksums generated | NOT EXECUTED | No build artifacts |
| Checksums verified against artifacts | NOT EXECUTED | No artifacts to verify |
| `SHA256SUMS.txt` format | DOCUMENTED | `release.yml` defines format |

---

## 11. Rollback and Recovery Documentation

**Status: PARTIALLY VERIFIED**

| Aspect | Status | Details |
|--------|--------|---------|
| Last known-good artifact | DOCUMENTED | Previous GitHub Release assets remain available |
| Application rollback | DOCUMENTED | Uninstall previous version, reinstall previous |
| Configuration rollback | DOCUMENTED | `config.toml.bak` created by auto-discovery |
| Data migration | NOT APPLICABLE | No data migration between versions |
| Rollback drill | NOT PERFORMED | No drill executed |

**Evidence:** `docs/release.md` documents rollback paths.

---

## 12. Release Workflow Gates

**Status: VERIFIED**

| Gate | Job | Status |
|------|-----|--------|
| Gate 1: Validation | `validate-release` (ubuntu-latest) | TESTED — 12/12 CI checks passing |
| Gate 2: Build | `build-installer` (windows-latest, `needs: validate-release`) | NOT EXECUTED — requires Windows runner with NSIS |
| Gate 3: Release publication | MANUAL | NOT CREATED — no automatic publish |

**Evidence:** `.github/workflows/release.yml` — two sequential jobs with `needs:` dependency; no `softprops/action-gh-release` step.

---

## 13. Blocker Summary

| Blocker | Severity | Impact | Required Action |
|---------|----------|--------|-----------------|
| No code-signing certificate | High | Release builds unsigned; SmartScreen warnings | Acquire certificate; configure `AUTODJ_PFX`/`AUTODJ_PFX_PASSWORD` CI secrets |
| No Windows build execution | Medium | Installer compilation not verified | Run release workflow on Windows runner with NSIS |
| SBOM not generated | Low | No supply chain verification artifact | Run `cyclonedx-py` in release workflow |
| Provenance not attested | Low | No build attestation | Run `attest-build-provenance` in release workflow |
| No release tag signing procedure executed | Medium | No cryptographic proof of tag identity | Follow `AUTODJ_RELEASE_SIGNING_PROCEDURE.md` for v0.2.7+ |

---

## 14. Release Candidate Qualification Verdict

**Status: CONDITIONALLY QUALIFIED**

| Gate | Status |
|------|--------|
| Version consistency | VERIFIED |
| CHANGEML completeness | VERIFIED |
| Dependency reproducibility | VERIFIED |
| Build reproducibility | UNVERIFIED |
| SBOM verification | NOT EXECUTED |
| Provenance verification | NOT EXECUTED |
| Signed artifacts | BLOCKED — certificate required |
| GPG-signed tag procedure | DOCUMENTED (not executed) |
| Artifact checksums | NOT EXECUTED |
| Rollback documentation | PARTIALLY VERIFIED |
| Release workflow gates | VERIFIED |

**The release candidate cannot be produced without:** (1) a code-signing certificate, (2) a Windows build environment, and (3) manual release creation by a maintainer.

**The existing unsigned v0.2.6 tag remains unchanged.**

---

## 15. Steps to Produce Release Candidate

1. Acquire code-signing certificate from public CA
2. Configure `AUTODJ_PFX` and `AUTODJ_PFX_PASSWORD` (or `AUTODJ_CERT_THUMBPRINT`) as GitHub secrets
3. Run release workflow on Windows runner to build signed artifacts
4. Verify SHA256 checksums against `SHA256SUMS.txt`
5. Verify provenance attestation
6. Create GPG-signed annotated tag following `AUTODJ_RELEASE_SIGNING_PROCEDURE.md`
7. Independent reviewer (`policedbc`) verifies tag signature
8. Maintainer (`cvsz`) creates release manually with artifacts, SBOM, checksums
