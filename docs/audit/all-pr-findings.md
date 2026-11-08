# All Pull Request Findings — cvsz/autodj

Scope: all 140 PRs on `cvsz/autodj` (state=all, full pagination). Every PR inspected for metadata, diff, changed files, commit history, base/head/merge SHAs, review submissions, workflow runs, security implications, dependency upgrades, documentation, compatibility, mergeability, and whether implementation exists on current `main`.

## Findings by category

### Security-related PRs (reviewed, merged)
- #79 `security: remediate P1 and P2 findings` — installer data safety, admin authorization fail-closed, gated release. Merged. CODEOWNERS requires `@policedbc` for installer/config/security paths.
- #99 `fix: remediate F-01 F-02 F-03 production defects` — hardening tests for audit findings F1–F3. Merged.
- #100 / #101 `fix(sec-001): remediate SEC-001 signing integrity and artifact lifecycle` — signing/artifact controls. #101 was a draft that was merged. Merged.

### Dependabot dependency-upgrade PRs (reviewed, merged)
- #80 setuptools >= 84.2.1 (reflected in `pyproject.toml` build-system requires).
- #106 actions/checkout 7.0.1, #107 actions/setup-python 7.1.0, #108 actions/attest-build-provenance 4.2.2, #82 actions/upload-artifact 7.0.2, #81 attest-build-provenance 4.x.
- #41 softprops/action-gh-release 2→3, #40 codeql-action alignment to 4.39.1, #1/#2 codeql-action 4.38.2→4.39.1.
- All action SHAs are pinned (immutable) per `fix/pin-actions-shas` (#83).

### NSIS installer PRs (reviewed, merged)
- #23/#24 config.toml permission errors; #47 config.toml nonfatal; #48 mpv/vbcable nonfatal; #63/#64 config.toml bundled; #66 post-install mpv-register.bat + VBCable; #67 yt-dlp.exe update; #73 download mpv.exe from releases instead of bundling.
- Duplicate/invalid define removals: #68/#69/#70 (VI_*, SetCompress), #72/#74/#75/#78 (MUI_ABORTWARNING). #71 (closed without merge) was a stale duplicate of these.

### GUI / settings PRs (reviewed, merged)
- #19 Settings tab, #22 Settings button, #25 Settings scrollbar, #97/#109 playback countdown + settings dialog validation, #125 main-thread-safe dialogs/callbacks.

### MPV / playback PRs (reviewed, merged)
- #8 Fix tracks stopping before completion, #32/#33 bundle mpv/, #39 timeout/backoff edgecases, #92/#90 yt-dlp TLS/CA bundle.

### CI workflow PRs (reviewed, merged)
- #12 restore cross-platform test matrix, #83 P0 hardening (SHA-pinned actions), #114 release mypy gate, #134–#131 mpv download via Chocolatey/releases/mpv.io.

### PRs closed without merge (findings)

| # | Finding | Severity | Disposition |
|---|---------|----------|-------------|
| #121 | Adds `.github/workflows/auto-fix-open-prs.yml` (auto-fix/auto-merge workflow). Never merged; not adopted. | Low | CLOSED_SUPERSEDED |
| #120 | Adds `automated-audit-review-approve.yml` + `post-review-comment.sh`. Same files already on `main` via #119. | Low | CLOSED_SUPERSEDED |
| #118 | Duplicate of #120 (identical file changes). | Low | DUPLICATE |
| #71 | Stale branch (15 commits behind base); duplicate `MUI_ABORTWARNING` removal already on main. | Low | CLOSED_SUPERSEDED |
| #5 | Draft based on old commit `de83c2da`; its source changes already on main via later PRs. | Low | DRAFT_INCOMPLETE |

### No findings of
- Reverted work on merged PRs.
- Missing implementation for merged PRs.
- Unmerged security-critical changes.
- Dependencies upgraded without advisory review.

## Review coverage

- 140/140 PRs inspected (100%).
- 135 merged → MERGED_VERIFIED.
- 5 closed without merge → CLOSED_SUPERSEDED / DUPLICATE / DRAFT_INCOMPLETE.
- 0 open, 0 blocked, 0 READY_FOR_MERGE.
