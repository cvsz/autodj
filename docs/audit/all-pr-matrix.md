# All Pull Request Matrix — cvsz/autodj

Classification key:

- `MERGED_VERIFIED` — PR merged and implementation confirmed present on current `main` (HEAD `9a5e8298`).
- `OPEN_ACTION_REQUIRED` — open PR needing work. (None currently open.)
- `DRAFT_INCOMPLETE` — Draft PR, closed without merge; implementation incomplete or superseded.
- `CLOSED_SUPERSEDED` — closed without merge; equivalent work already in `main` via another PR, or branch stale/behind base.
- `DUPLICATE` — duplicates another PR's changes; no unique work to recover.
- `SECURITY_REVIEW_REQUIRED` — none identified separately; security PRs (#79, #99–#101) were merged and reviewed.
- `BLOCKED` — none.
- `READY_FOR_MERGE` — none (no open PRs).

## Merged (135)

All merged PRs are reachable from current `main`. Disposition recorded per PR below.

| # | Disposition | Title |
|---|-------------|-------|
| 141 | MERGED_VERIFIED | docs: sync final-report.md with latest enterprise validation results |
| 140 | MERGED_VERIFIED | docs: sync final-report.md with latest enterprise validation results |
| 139 | MERGED_VERIFIED | docs: create final-report.md with full enterprise audit and remediation details |
| 138 | MERGED_VERIFIED | fix: remove 2>/dev/null suppression from YAML validation in auto-fix-loop |
| 137 | MERGED_VERIFIED | merge: integrate origin/main and unreleased v0.2.8 release commits into main |
| 136 | MERGED_VERIFIED | chore: merge AutoDJ v0.2.8 release |
| 135 | MERGED_VERIFIED | chore: bump version to 0.2.8 |
| 134 | MERGED_VERIFIED | ci: download mpv from mpv.io direct link |
| 133 | MERGED_VERIFIED | ci: download mpv from official GitHub releases |
| 132 | MERGED_VERIFIED | ci: comprehensive mpv.exe search after Chocolatey install |
| 131 | MERGED_VERIFIED | ci: add refreshenv and fallback paths for mpv Chocolatey install |
| 130 | MERGED_VERIFIED | ci: use Get-Command to find mpv.exe after Chocolatey install |
| 129 | MERGED_VERIFIED | ci: fix mpv path detection for Chocolatey install |
| 128 | MERGED_VERIFIED | ci: use Chocolatey to install mpv for release build |
| 127 | MERGED_VERIFIED | ci: add mpv download step to release workflow |
| 126 | MERGED_VERIFIED | feat: Premium Enterprise UI + IM Auto-Reply + Auto-Reply System |
| 125 | MERGED_VERIFIED | fix: make GUI dialogs and callbacks main-thread safe |
| 124 | MERGED_VERIFIED | fix: remediate enterprise audit findings — passphrases, invalid configs, output |
| 123 | MERGED_VERIFIED | fix: harden workflows — address policedbc security review |
| 122 | MERGED_VERIFIED | fix: harden workflows for enterprise production grade |
| 119 | MERGED_VERIFIED | feat: add auto audit/review/approve workflow |
| 117 | MERGED_VERIFIED | test: auto-audit workflow trigger v2 |
| 116 | MERGED_VERIFIED | test: auto-audit workflow trigger |
| 115 | MERGED_VERIFIED | docs: mark placeholder Dockerfile checklist item VERIFIED |
| 114 | MERGED_VERIFIED | build: add local audit image zpostgresql; fix release mypy gate; apply ruff form |
| 113 | MERGED_VERIFIED | feat: autodj enhancements and fixes |
| 112 | MERGED_VERIFIED | fix: security hardening — backup before repo overwrite, fail-closed admin authorization |
| 111 | MERGED_VERIFIED | style: remove unused noqa in __main__.py |
| 110 | MERGED_VERIFIED | style: ruff format 12 files |
| 109 | MERGED_VERIFIED | fix: player music time countdown; fix settings dialog NameError; add input validation |
| 108 | MERGED_VERIFIED | chore(deps): bump actions/attest-build-provenance from 2.4.0 to 4.2.2 |
| 107 | MERGED_VERIFIED | chore(deps): bump actions/setup-python from 5.6.0 to 7.1.0 |
| 106 | MERGED_VERIFIED | chore(deps): bump actions/checkout from 4.2.2 to 7.0.1 |
| 105 | MERGED_VERIFIED | docs: update Final-Report.md with all PRs merged status |
| 104 | MERGED_VERIFIED | fix(test): update upload-artifact SHA for v7.0.2 in release consistency test |
| 103 | MERGED_VERIFIED | docs: update Final-Report.md with release completion status |
| 102 | MERGED_VERIFIED | fix: player music time countdown; harden exception handling across modules |
| 101 | MERGED_VERIFIED | fix(sec-001): remediate SEC-001 signing integrity and artifact lifecycle (draft label, merged) |
| 100 | MERGED_VERIFIED | fix(sec-001): remediate SEC-001 signing integrity and artifact lifecycle |
| 99 | MERGED_VERIFIED | fix: remediate F-01 F-02 F-03 production defects |
| 98 | MERGED_VERIFIED | fix(gui): show settings dialog content |
| 97 | MERGED_VERIFIED | fix(gui): show remaining playback time countdown |
| 96 | MERGED_VERIFIED | fix(test): fix Windows test compatibility issues |
| 95 | MERGED_VERIFIED | fix(lint): cleanup ruff/mypy issues in migration code |
| 94 | MERGED_VERIFIED | fix(config): safe configuration migration for placeholder values (v2) |
| 93 | MERGED_VERIFIED | fix(config): safe configuration migration for placeholder values |
| 92 | MERGED_VERIFIED | fix(library): yt-dlp TLS trust integration - SSL fallback from exe to Python module |
| 91 | MERGED_VERIFIED | fix(ps-qualification-scripts): repair PowerShell 5.1 compatibility in qualification scripts |
| 90 | MERGED_VERIFIED | fix(library): correct yt-dlp CA bundle integration |
| 89 | MERGED_VERIFIED | fix(production-runtime): add observability diagnostics and comprehensive regression tests |
| 88 | MERGED_VERIFIED | fix(production-runtime): complete P1/P2 remediation |
| 87 | MERGED_VERIFIED | qual: Windows Qualification Kit PowerShell script fixes |
| 86 | MERGED_VERIFIED | qual: Windows Qualification Kit |
| 85 | MERGED_VERIFIED | qual: production qualification acceptance reports |
| 84 | MERGED_VERIFIED | qual: production qualification reports and installer recovery fix |
| 83 | MERGED_VERIFIED | ci: complete P0 hardening — SHA-pinned actions, release readiness reports |
| 82 | MERGED_VERIFIED | chore(deps): bump actions/upload-artifact from 4.6.2 to 7.0.2 |
| 81 | MERGED_VERIFIED | chore(deps): bump actions/attest-build-provenance from 4 to 4.2.2 |
| 80 | MERGED_VERIFIED | chore(deps-dev): update setuptools requirement from >=68 to >=84.2.1 |
| 79 | MERGED_VERIFIED | security: remediate P1 and P2 findings (installer data safety, admin authorization, gated release) |
| 78 | MERGED_VERIFIED | fix: remove duplicate MUI_ABORTWARNING define from installer.nsi |
| 77 | MERGED_VERIFIED | checklist: mark all implementation checklist items complete |
| 76 | MERGED_VERIFIED | fix: harden executable resolution and preserve user data |
| 75 | MERGED_VERIFIED | fix: remove duplicate MUI_ABORTWARNING define from installer.nsi |
| 74 | MERGED_VERIFIED | fix: remove duplicate MUI_ABORTWARNING define from installer.nsi |
| 73 | MERGED_VERIFIED | fix: download mpv.exe from GitHub releases instead of bundling |
| 72 | MERGED_VERIFIED | fix: remove invalid MUI_ABORTWARNING define from installer.nsi |
| 70 | MERGED_VERIFIED | fix: remove invalid SetCompress line from installer.nsi |
| 69 | MERGED_VERIFIED | fix: remove invalid SetCompress line from installer.nsi |
| 68 | MERGED_VERIFIED | fix: remove invalid VI_* defines from installer.nsi |
| 67 | MERGED_VERIFIED | feat: update yt-dlp.exe to latest version |
| 66 | MERGED_VERIFIED | fix: add post-install mpv-register.bat and VBCABLE_Setup_x64.exe silent execution |
| 65 | MERGED_VERIFIED | docs: update AutoDJ-Final-Report.md with residual risks, rollback, next actions |
| 64 | MERGED_VERIFIED | feat: bundle standard config.toml in NSIS installer |
| 63 | MERGED_VERIFIED | docs: add AutoDJ-Final-Report.md complete project report |
| 62 | MERGED_VERIFIED | feat: add validate-template target to Makefile |
| 61 | MERGED_VERIFIED | chore: cleanup unused scripts and update github_admin default repo |
| 60 | MERGED_VERIFIED | fix: load folder button crash on permission-denied directories |
| 59 | MERGED_VERIFIED | fix: protect log file creation against PermissionError on startup |
| 58 | MERGED_VERIFIED | fix: protect log file creation against PermissionError on startup |
| 57 | MERGED_VERIFIED | fix: settings config.toml write, hidden CMD launcher, type safety |
| 56 | MERGED_VERIFIED | fix: make playlist yt-dlp resolution TLS-safe across platforms |
| 55 | MERGED_VERIFIED | docs: add v0.2.6 release audit, security, acceptance and operational handover reports |
| 54 | MERGED_VERIFIED | chore: release Camfrog AutoDJ v0.2.6 |
| 53 | MERGED_VERIFIED | docs: add v0.2.5 official release handover report (#53) |
| 52 | MERGED_VERIFIED | docs: add v0.2.5 final release gate audit and acceptance report |
| 51 | MERGED_VERIFIED | docs: add v0.2.5 baseline, release, and final verification reports |
| 50 | MERGED_VERIFIED | fix(ci): match installer artifact pattern Camfrog-AutoDJ-Setup-*.exe |
| 49 | MERGED_VERIFIED | fix(ci): use cyclonedx-py environment with -o flag for SBOM generation |
| 48 | MERGED_VERIFIED | fix(installer): mark external mpv and vbcable as nonfatal |
| 47 | MERGED_VERIFIED | fix(installer): make config.toml nonfatal in NSIS script |
| 46 | MERGED_VERIFIED | fix(ci): add NSIS to path for Windows release runner |
| 45 | MERGED_VERIFIED | feat: v0.2.5 audio fade, dynamic normalization, moderation, and SBOM attestation |
| 44 | MERGED_VERIFIED | docs: sync playlist pack guidance and installer spec with 0.2.5 dynamic resolution |
| 43 | MERGED_VERIFIED | chore: bump and sync version 0.2.5 across docs, manifests, and build scripts |
| 42 | MERGED_VERIFIED | feat: dynamic search resolution and lookahead preloading for playlist tracks |
| 41 | MERGED_VERIFIED | chore(deps): bump softprops/action-gh-release from 2 to 3 |
| 40 | MERGED_VERIFIED | fix(ci): align CodeQL action steps to v4.39.1 and configure dependabot group |
| 39 | MERGED_VERIFIED | fix: resolve timeout and failure backoff edgecases in engine and player |
| 38 | MERGED_VERIFIED | fix: gracefully handle missing join_uri_template in launcher |
| 37 | MERGED_VERIFIED | fix: add window support to fake_tk for Settings tab scrollbar |
| 36 | MERGED_VERIFIED | fix: fix NameError in auto_launch exception handler |
| 35 | MERGED_VERIFIED | fix: fix NameError when auto_launch fails |
| 34 | MERGED_VERIFIED | fix: auto-launch crash prevents GUI from opening |
| 33 | MERGED_VERIFIED | fix: bundle mpv.exe from system when mpv/ not in repo |
| 32 | MERGED_VERIFIED | fix: bundle mpv/ with AutoDJ.exe |
| 31 | MERGED_VERIFIED | fix: log file directory not created |
| 30 | MERGED_VERIFIED | fix: config.example.toml use relative mpv_path and ytdlp_path |
| 29 | MERGED_VERIFIED | fix: include config.toml in installer |
| 28 | MERGED_VERIFIED | fix: config.toml PermissionError on Program Files install |
| 27 | MERGED_VERIFIED | fix: playlist not play when mpv not available |
| 26 | MERGED_VERIFIED | fix: config.toml log_file PermissionError on Program Files install |
| 25 | MERGED_VERIFIED | fix: Settings tab scrollbar - Save button was off-screen |
| 24 | MERGED_VERIFIED | fix: NSIS installer config.toml read permission error |
| 23 | MERGED_VERIFIED | fix: NSIS installer config.toml permission error |
| 22 | MERGED_VERIFIED | feat: add Settings button to GUI header |
| 21 | MERGED_VERIFIED | fix: NSIS installer CheckExistingInstall - remove StrReplace dependency |
| 20 | MERGED_VERIFIED | fix: NSIS installer CheckExistingInstall GetParameters error |
| 19 | MERGED_VERIFIED | feat: add Settings tab to GUI |
| 18 | MERGED_VERIFIED | config: update config.example.toml for installer layout |
| 17 | MERGED_VERIFIED | fix: NSIS installer - auto-uninstall old version, add mpv + yt-dlp + VBCable |
| 16 | MERGED_VERIFIED | docs: sync CHANGELOG, README, Makefile with 0.2.5 release |
| 15 | MERGED_VERIFIED | docs: sync CHANGELOG, README, Makefile with 0.2.5 release |
| 14 | MERGED_VERIFIED | fix: eliminate NSIS installer warnings, remove src section |
| 13 | MERGED_VERIFIED | fix: eliminate NSIS installer warnings, remove src section |
| 12 | MERGED_VERIFIED | fix(ci): restore cross-platform test matrix |
| 11 | MERGED_VERIFIED | chore: exclude build artifacts, binaries, debug scripts, forensic files |
| 10 | MERGED_VERIFIED | chore: exclude build artifacts, binaries, debug scripts, forensic files |
| 9 | MERGED_VERIFIED | release: v0.2.4 enterprise production fixes |
| 8 | MERGED_VERIFIED | Fix tracks stopping before completion |
| 7 | MERGED_VERIFIED | build(deps): bump actions/setup-python from 5 to 7 |
| 6 | MERGED_VERIFIED | build(deps): bump actions/checkout from 4 to 7 |
| 2 | MERGED_VERIFIED | chore(deps): bump github/codeql-action/init from 4.38.2 to 4.39.1 |
| 1 | MERGED_VERIFIED | chore(deps): bump github/codeql-action/analyze from 4.38.2 to 4.39.1 |

## Closed without merge (5)

| # | Disposition | Title | Reason |
|---|-------------|-------|--------|
| 121 | CLOSED_SUPERSEDED | feat: add auto-fix open PRs workflow | Branch closed without merge; adds `.github/workflows/auto-fix-open-prs.yml` which was never adopted. No unique application-code work to recover. |
| 120 | CLOSED_SUPERSEDED | feat: add auto audit/review/approve workflow | Branch closed without merge; its changes (`.github/scripts/post-review-comment.sh`, `.github/workflows/automated-audit-review-approve.yml`) are already present on `main` via PR #119. |
| 118 | DUPLICATE | feat: add auto audit/review/approve workflow | Byte-for-byte duplicate of PR #120's changes; same files. Superseded by #120/#119. |
| 71 | CLOSED_SUPERSEDED | fix: remove duplicate MUI_ABORTWARNING define from installer.nsi | Branch is 15 commits behind its base (stale); the duplicate-define removal is already in `main` (PRs #78/#75/#74). |
| 5 | DRAFT_INCOMPLETE | fix(ci): restore deterministic AutoDJ test baseline | Draft, based on old commit `de83c2da` (33 commits behind current main). Its source changes (config.mpv_timeout default, discover.choose_view, gui.close guard, library.find_ytdlp, player._is_windows) are already present on `main` via later PRs (#97/#109/#88/etc.). Nothing to recover. |

## Drafts (3)

| # | State | Merged? | Title | Note |
|---|-------|---------|-------|------|
| 101 | closed | Yes | fix(sec-001): remediate SEC-001 signing integrity and artifact lifecycle | Merged despite draft label; SEC-001 signing-integrity remediation present on main. |
| 4 | closed | Yes | fix(ci): align CodeQL action versions | Merged despite draft label; CodeQL v4.39.1 alignment present on main. |
| 5 | closed | No | fix(ci): restore deterministic AutoDJ test baseline | See closed-without-merge above. |

## Verification note

Every `MERGED_VERIFIED` PR's changes are ancestors of current `main` (`9a5e8298`). No reverted work or missing implementation was detected for merged PRs. The 5 closed-without-merge PRs contain no unique application-code work that is absent from `main`.
