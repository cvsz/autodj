# Camfrog AutoDJ v0.2.5 — Baseline Discovery & Architecture Audit

**Date:** 2026-11-01  
**Auditor:** Super Ultra AI ORC (Principal Systems Architect & Release Orchestrator)  
**Target Release:** `v0.2.5`  
**Repository:** `cvsz/autodj`  

---

## 1. Executive Summary

This comprehensive baseline discovery and architecture audit examines `cvsz/autodj` prior to official release orchestration and product enhancements. The repository is on `main` at commit `264409c` (Merge PR #44). The latest published release tag on GitHub is `v0.2.4`, making `v0.2.5` a clean, unreleased, eligible release target.

All 140 unit and integration tests are passing cleanly on Python 3.14 / 3.11 / 3.12 matrices. Packaging, configuration, and documentation versions have been aligned to `0.2.5`.

---

## 2. Current Architecture & Component Inspection

### 2.1 Core Runtime & Engine (`camfrog_autodj/engine.py`)
- **Queue & Playback Management:** `Queue` manages request queues (`requests`) and autoplay pools (`pool`). Playback loop (`_player_loop`) pops tracks and streams via `player.play()`.
- **Dynamic Search Resolution (Added in PR #42):** Search-backed queries (`ytsearch1:...`) from playlist files are resolved asynchronously via lookahead preloading (`_preload_search_tracks`) and just-in-time in `_player_loop`.
- **Concurrency & Threads:** Multi-threaded architecture utilizing daemon worker threads tracked in `self._threads` (`_sender`, `_player_loop`, `_load_all`, `_chat_loop`).

### 2.2 Player Layer (`camfrog_autodj/player.py`)
- Subprocesses `mpv` with IPC pipes / socket command interface.
- Volume management: volume set via IPC property write `set_property volume`.
- Missing capabilities: Audio fade-in / fade-out, crossfade, and automated dynamic audio normalization filters (`loudnorm` / `dynaudnorm`).

### 2.3 Library & YouTube Integration (`camfrog_autodj/library.py`)
- Resolves queries via `yt-dlp` CLI subprocess (`--dump-single-json`, `--flat-playlist`).
- Missing capabilities: YouTube cookies / authentication (`--cookies`, `--cookies-from-browser`).

### 2.4 Camfrog Chat & Bot Automation (`camfrog_autodj/commands.py` & `adapters/uia.py`)
- Windows UI Automation (`uia.py`) attaches to Camfrog Desktop room window, reads chat, and sends messages.
- Command router implements `!play`, `!voteskip`, `!queue`, `!np`, `!last`, `!cooldown`.
- Cooldown model: Single timestamp per user `now - last[who] < cooldown`.
- Voteskip: Basic count against static threshold `len(votes) >= voteskip_threshold`. Dynamic quorum based on room count is absent.

### 2.5 Desktop GUI (`camfrog_autodj/gui.py`)
- Modernized Tkinter application with custom dark canvas widgets (glow bars, confetti, tabbed views for Queue, History, Chat, and Settings).
- Missing capabilities: In-GUI YouTube search & quick add, Light/Dark theme toggle.

### 2.6 Installer & Release Pipeline (`installer.nsi`, `.github/workflows/release.yml`)
- NSIS Modern UI 2 installer (`Camfrog-AutoDJ-Setup-0.2.5.exe`) built via `build.ps1` + `installer.nsi`.
- Release workflow pins GitHub Action release publisher (`softprops/action-gh-release@v3`).
- Missing supply-chain capabilities: Automated CycloneDX SBOM generation, GitHub Artifact Attestation (`actions/attest-build-provenance`).

---

## 3. Findings & Technical Debt Matrix

| Category | Finding / Gap | Priority | Recommendation |
|---|---|---|---|
| **Audio** | No audio fade-in/out or loudness normalization | High | Implement smooth volume ramping in `MpvPlayer` and `dynaudnorm` filter options |
| **YouTube** | No cookie authentication option for age/geo-restricted streams | Medium | Add `cookies_file` and `cookies_from_browser` config options to `library.py` |
| **Bot** | Voteskip threshold is static only | Medium | Support dynamic percentage of room participants where available |
| **Bot** | Cooldown is single-shot per user | Medium | Retain monotonic rate limiter with clean time windows |
| **GUI** | No YouTube search tab or quick-add dialog | High | Add search entry & async results table in GUI |
| **Supply Chain** | No SBOM or GitHub Artifact Attestation in release workflow | High | Integrate CycloneDX SBOM and `actions/attest-build-provenance` |

---

## 4. Release Readiness Gate

- **Target Version:** `0.2.5`
- **Current Git Tag Status:** `v0.2.4` exists; `v0.2.5` does NOT exist.
- **Milestone:** Eligible for official creation and release.
- **Verification Strategy:** Feature branches -> Local pytest -> GPG Commit -> PR -> policedbc review -> cvsz merge -> Tag `v0.2.5`.

---
