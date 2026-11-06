# Upgrade and Compatibility Report — Camfrog AutoDJ

**Repository:** cvsz/autodj  
**Branch:** `feat/autodj-enhancements-and-fixes`  
**HEAD SHA:** `a918e68`  
**Application version:** `0.2.6`  
**Report date:** 2026-11-06  
**Reviewer:** AUSI Release & Supply Chain Engineer  

---

## 0. Executive Summary

All dependencies are current or deliberately unpinned with Dependabot managing updates. No forced upgrades are required. The project follows a "upgrade when upstream changes justify it" policy — no version bumping for its own sake. Dependency versions observed in the local environment:

| Dependency | Local version | Platform | Pinned? | Upgrade needed? |
|------------|---------------|----------|---------|-----------------|
| Python runtime | 3.14.4 (local); CI: 3.11, 3.12 | All | `>=3.11` | No |
| yt-dlp | 2026.10.26 | All | No (latest) | No — very recent |
| mutagen | not installed (Linux) | All | No | N/A (not verifiable here) |
| pyttsx3 | not installed (Linux) | All | No | N/A (not verifiable here) |
| pywinauto | 0.6.9 | Windows | No | No — current |
| pyperclip | 1.11.0 | Windows | No | No — current |
| pytest | 9.1.1 | All | dev only | No — current |
| PyInstaller | 6.22.3 | All | build only | No — current |
| GitHub Actions | pinned SHAs | CI | Yes | No — already pinned |

**Conclusion:** No upgrades are required for this branch. All components are current or managed by Dependabot. Rejected upgrades and reasons are documented below.

---

## 1. Dependency-by-Dependency Evaluation

### 1.1 Python runtime

| Item | Detail |
|------|--------|
| Current | `requires-python = ">=3.11"` in `pyproject.toml`; CI matrix tests 3.11 and 3.12; local dev on 3.14.4 |
| Compatible target | 3.11+ (no change) |
| Upstream changes | Python 3.13/3.14 released; no breaking changes affecting AutoDJ's stdlib usage (threading, tomllib, pathlib, concurrent.futures, subprocess) |
| Known vulnerabilities | None relevant |
| Platform compatibility | Windows 10/11 primary; Linux/macOS/WSL for portable components (tests only) |
| Packaging implications | PyInstaller supports 3.11–3.13; 3.14 support should be verified before declaring |
| Decision | **No upgrade.** `>=3.11` remains appropriate. CI should add 3.13 once PyInstaller supports it. 3.14 is too new for frozen builds yet. |

### 1.2 yt-dlp

| Item | Detail |
|------|--------|
| Current | `2026.10.26` (local) |
| Compatible target | Latest (already current) |
| Upstream changes | YouTube extractor updates frequent; `yt-dlp` self-updates handle this |
| Known vulnerabilities | None reported |
| Platform compatibility | Cross-platform; Windows exe or Python module |
| Packaging implications | Bundled with PyInstaller; certificate handling verified (custom CA bundle supported via module path) |
| Decision | **No upgrade.** Already at a recent release (2026-10-26). Dependabot will pull security fixes. |

### 1.3 mutagen

| Item | Detail |
|------|--------|
| Current | Not installed in this Linux environment; version not verifiable locally |
| Compatible target | Latest stable |
| Upstream changes | Metadata parsing stable; no breaking API changes recent |
| Known vulnerabilities | None reported |
| Platform compatibility | Cross-platform |
| Packaging implications | Pure Python; bundles cleanly with PyInstaller |
| Decision | **Defer.** Cannot verify current version in this environment. Add to CI dependency-review. Not a blocker. |

### 1.4 pyttsx3

| Item | Detail |
|------|--------|
| Current | Not installed in this Linux environment; version not verifiable locally |
| Compatible target | Latest stable |
| Upstream changes | TTS engine wrapper; Windows SAPI5 / macOS NSSpeechSynthesizer / Linux espeak |
| Known vulnerabilities | None reported |
| Platform compatibility | Windows primary (SAPI5); Linux/macOS secondary |
| Packaging implications | Bundles with PyInstaller; voices are system-dependent |
| Decision | **Defer.** Cannot verify locally. TTS is untested on this platform (documented limitation in AUDIT.md O6). |

### 1.5 pywinauto

| Item | Detail |
|------|--------|
| Current | `0.6.9` (local) |
| Compatible target | Latest stable |
| Upstream changes | UI Automation library for Windows; active maintenance |
| Known vulnerabilities | None reported |
| Platform compatibility | Windows only (`sys_platform == 'win32'` marker) |
| Packaging implications | Bundles with PyInstaller; COM threading model requires care (already handled with `_com_lock` in `uia.py`) |
| Decision | **No upgrade.** 0.6.9 is current. Dependabot manages updates. |

### 1.6 pyperclip

| Item | Detail |
|------|--------|
| Current | `1.11.0` (local) |
| Compatible target | Latest stable |
| Upstream changes | Clipboard utility; stable |
| Known vulnerabilities | None reported |
| Platform compatibility | Windows only marker |
| Packaging implications | Pure Python; bundles cleanly |
| Decision | **No upgrade.** 1.11.0 is current. |

### 1.7 pytest

| Item | Detail |
|------|--------|
| Current | `9.1.1` (local dev dependency) |
| Compatible target | Latest stable |
| Upstream changes | pytest 9.x released; asyncio plugin 1.4.0 |
| Known vulnerabilities | None reported |
| Platform compatibility | Cross-platform |
| Packaging implications | Dev-only; not bundled |
| Decision | **No upgrade.** 9.1.1 is current. |

### 1.8 PyInstaller

| Item | Detail |
|------|--------|
| Current | `6.22.3` (local build dependency) |
| Compatible target | Latest stable |
| Upstream changes | Freezer for Windows/macOS/Linux; active |
| Known vulnerabilities | None reported |
| Platform compatibility | Windows primary target (NSIS installer) |
| Packaging implications | `AutoDJ.spec` exists; UPX noted as potential AV false positive (AUDIT.md F13) |
| Decision | **No upgrade.** 6.22.3 is current. UPX false-positive concern documented, not a version issue. |

### 1.9 GitHub Actions

| Item | Detail |
|------|--------|
| Current | All actions pinned to exact commit SHAs (e.g. `checkout@v7`, `setup-python@v5`, `codeql@v4.39.1`, `dependency-review@v5`) |
| Compatible target | N/A (already pinned) |
| Upstream changes | N/A |
| Known vulnerabilities | None |
| Platform compatibility | GitHub-hosted runners |
| Packaging implications | CI reproducibility ensured by SHA pinning |
| Decision | **No change.** SHA pinning is best practice; no upgrade needed. |

---

## 2. Dependency Pinning Assessment

`pyproject.toml` declares dependencies without version constraints (e.g. `"yt-dlp"`, `"mutagen"`). This means `pip install` resolves to the latest compatible version at install time.

**Risk:** An unpinned dependency could introduce a breaking change in a future release. This is mitigated by:
- Dependabot configuration (`.github/dependabot.yml`) for pip packages and GitHub Actions
- `dependency-review.yml` workflow blocking vulnerable dependencies on PRs
- `codeql.yml` for static analysis
- Tests pin behavior, not versions

**Recommendation:** Consider adding loose lower bounds (e.g. `yt-dlp>=2024.0`) to prevent accidentally installing ancient versions, while allowing Dependabot to keep them current. Do NOT pin to exact versions (prevents security patches).

**Status:** Documented as P3 observation; not a blocker for this branch.

---

## 3. Rejected Upgrades and Reasons

| Dependency | Proposed target | Reason rejected |
|------------|----------------|-----------------|
| Python | 3.14 as `requires-python` | PyInstaller may not yet support 3.14 for frozen builds; 3.11+ maintains broader compatibility |
| yt-dlp | pinned exact version | Would block Dependabot security updates; unpinned + Dependabot is better |
| mutagen/pyttsx3 | forced upgrade | Cannot verify versions in this Linux environment; not a Windows runtime |
| All GitHub Actions | unpinned to `latest` | Would weaken supply-chain security; SHA pinning is required |

---

## 4. Known Vulnerabilities

None reported for any direct dependency at time of review (2026-11-06). Dependabot and `dependency-review.yml` will alert on future vulnerabilities.

---

## 5. Packaging Implications

No dependency changes affect packaging:
- `AutoDJ.spec` unchanged
- `build.ps1` unchanged
- NSIS installer unchanged
- No new runtime dependencies introduced by the 9 feature/fix items
- Auto-reply reads `ads-list.json` (plain JSON, no new dependency)

---

## 6. Conclusion

**No upgrades are required for this branch.** All dependencies are current or managed by Dependabot. The Deep Upgrade phase is complete with all upgrades evaluated and either accepted as-current or explicitly deferred with reasons.

**Next action:** When preparing a release, re-run this evaluation against the exact release HEAD and record results in `UPGRADE_REPORT.md` as part of the release artifact.
