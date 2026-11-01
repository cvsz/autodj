# Camfrog AutoDJ v0.2.5 — Official Release Report

**Product:** Camfrog AutoDJ  
**Target Release:** `v0.2.5`  
**Organization:** ZEAZDEV COMPANY LIMITED  
**Repository:** `cvsz/autodj`  
**Base Commit (main):** `78dc321d9584a7da5a1248ad057d7ac244045569`

---

## 1. Executive Summary

This report documents the verification, governance, implementation, security hardening, and release automation executed for the official `v0.2.5` release program. All functional requirements, regression tests, packaging scripts, and CI/CD supply-chain hardening steps have been executed and validated against the repository codebase.

---

## 2. Completed Scope & Engineering Enhancements

### 2.1 Core Audio Engineering
- **Audio Fade Transitions:** Configured smooth audio fade-in on track start and fade-out on track end/skip via mpv IPC volume manipulation without blocking the main loop.
- **Dynamic Loudness Normalization:** Integrated `dynaudnorm` filter generation dynamically configurable through `config.toml` (`normalization_mode = "dynaudnorm"`).
- **YouTube Authentication & Cookies Support:** Added yt-dlp cookie arguments support (`youtube_cookies_browser` and `youtube_cookies_file`) with credential masking in exception strings.

### 2.2 Camfrog Chat & Bot Moderation
- **Dynamic Vote Skip:** Implemented dynamic threshold calculation based on active participant percentages with min/max caps (`voteskip_threshold`, `voteskip_dynamic`, `voteskip_dynamic_pct`). Duplicate user vote prevention and transition resets verified.
- **Sliding-Window Rate Limiting:** Enforced per-user sliding window request limits (`user_request_limit`, `rate_limit_window`) with case-insensitive username normalization and monotonic timestamping.

### 2.3 Windows GUI Modernization & Hi-DPI
- High-DPI Windows awareness (`SetProcessDpiAwarenessContext` / `SetProcessDPIAware`).
- Dark and Light theme switching support with persistent configuration.
- Inline YouTube search and quick queue integration.

### 2.4 Software Supply Chain Security & SBOM
- **CycloneDX SBOM:** Integrated `cyclonedx-py` environment scanning outputting machine-readable `Camfrog-AutoDJ-v0.2.5.cdx.json`.
- **GitHub Build Provenance & Attestation:** Added `actions/attest-build-provenance@v2` targeting the generated Windows installer (`Camfrog-AutoDJ-Setup-*.exe`) and CycloneDX SBOM.
- **NSIS Packaging Automation:** Enhanced `installer.nsi` and GitHub Actions `release.yml` with explicit makensis paths, GITHUB_PATH registration, and nonfatal bundling for headless CI runners.

---

## 3. Pull Request & Review Evidence

| PR | Title | Reviewer | Merger | Status |
|---|---|---|---|---|
| [#45](https://github.com/cvsz/autodj/pull/45) | feat: v0.2.5 audio fade, dynamic normalization, moderation, and SBOM attestation | `policedbc` (Approved) | `cvsz` | Merged (`2de8660`) |
| [#46](https://github.com/cvsz/autodj/pull/46) | fix(ci): add NSIS to path for Windows release runner | `policedbc` (Approved) | `cvsz` | Merged (`7f3a613`) |
| [#47](https://github.com/cvsz/autodj/pull/47) | fix(installer): make config.toml nonfatal in NSIS script | `policedbc` (Approved) | `cvsz` | Merged (`0f8f016`) |
| [#48](https://github.com/cvsz/autodj/pull/48) | fix(installer): mark external mpv and vbcable as nonfatal | `policedbc` (Approved) | `cvsz` | Merged (`c25d5da`) |
| [#49](https://github.com/cvsz/autodj/pull/49) | fix(ci): use cyclonedx-py environment with -o flag for SBOM generation | `policedbc` (Approved) | `cvsz` | Merged (`4c7c4d3`) |
| [#50](https://github.com/cvsz/autodj/pull/50) | fix(ci): match installer artifact pattern Camfrog-AutoDJ-Setup-*.exe | `policedbc` (Approved) | `cvsz` | Merged (`78dc321`) |

---

## 4. Test & Quality Gates

- **Unit & Regression Suite:** 143 passed in 3.59s (`pytest tests/`).
- **CodeQL Analysis:** Completed green across all PRs.
- **Dependency Review:** Completed green across all PRs.
- **Repository Baseline Check:** Completed green across all PRs.
- **Multi-Platform CI Matrix:** Ubuntu & Windows on Python 3.11 and 3.12 completed green across all PRs.

---

## 5. Artifact Verification & Build Evidence

- **Windows Installer Target:** `Camfrog-AutoDJ-Setup-0.2.5.exe` (NSIS Unicode 64-bit).
- **SBOM Target:** `Camfrog-AutoDJ-v0.2.5.cdx.json` (CycloneDX JSON spec 1.6).
- **Release Automation Run:** [#41285640249](https://github.com/cvsz/autodj/actions/runs/41285640249) succeeded in 2m 23s on Windows runner, compiling `AutoDJ.exe`, building `Camfrog-AutoDJ-Setup-0.2.5.exe`, generating CycloneDX SBOM, and producing cryptographic build provenance attestation.

---

## 6. Release Governance Note

Tag name `v0.2.5` was created and consumed during initial release workflow invocation. GitHub's immutable release policy restricts re-creating ref `v0.2.5` directly via remote push. The full release bundle, build provenance attestation, and SBOM have been verified on GitHub Actions run #41285640249.
