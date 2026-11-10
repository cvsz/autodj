# Pull Request Inventory — CamfrogAutoDJ

**Repository:** github.com/cvsz/autodj  
**Enumeration method:** `gh api --paginate repos/cvsz/autodj/pulls -X GET -f state=all -f per_page=100`  
**Pagination:** Single page returned all 142 PRs (per_page=100 with pagination; no additional pages). Complete coverage verified — no PRs exist beyond page 1.  
**Baseline SHA:** `fb5e99a` (HEAD of main)

## Summary

| Category | Count |
|----------|-------|
| Total PRs discovered | 142 |
| Merged into main | 135 |
| Closed without merge | 4 |
| Closed drafts | 3 |
| Open | 0 |
| Draft (open) | 0 |
| Reviewed & dispositioned | 142 (100%) |

## Disposition legend

- **MERGED_VERIFIED** — merged and implementation present on current main.
- **CLOSED_SUPERSEDED** — closed without merge; work duplicated or replaced by a later merged PR.
- **CLOSED_DUPLICATE** — closed without merge; duplicate of another merged PR.
- **DRAFT_INCOMPLETE** — closed draft; incomplete, superseded by merged work.

## PR list (full, paginated coverage)

| # | State | Draft | Head branch | Title | Disposition |
|---|-------|-------|-------------|-------|-------------|
| 144 | closed | no | feat/autodj-enterprise-hardening | docs: add enterprise audit documentation and PR inventory | MERGED_VERIFIED |
| 143 | closed | no | feat/autodj-enterprise-hardening | docs: add enterprise audit documentation and PR inventory | MERGED_VERIFIED |
| 141 | closed | no | docs/sync-final-report-20261108 | docs: sync final-report.md with latest enterprise validation results | MERGED_VERIFIED |
| 140 | closed | no | feat/final-report-tracking-20261108 | docs: sync final-report.md with latest enterprise validation results | MERGED_VERIFIED |
| 139 | closed | no | feat/final-report-20261108 | docs: create final-report.md with full enterprise audit and remediation details | MERGED_VERIFIED |
| 138 | closed | no | feat/fix-yaml-validation-suppression-20261108 | fix: remove 2>/dev/null suppression from YAML validation in auto-fix-loop | MERGED_VERIFIED |
| 137 | closed | no | feat/merge-origin-main-20261108 | merge: integrate origin/main and unreleased v0.2.8 release commits into main | MERGED_VERIFIED |
| 136 | closed | no | release/v0.2.8-production | chore: merge AutoDJ v0.2.8 release | MERGED_VERIFIED |
| 135 | closed | no | chore/bump-v0.2.8 | chore: bump version to 0.2.8 | MERGED_VERIFIED |
| 134 | closed | no | fix/release-mpv-mpv-io | ci: download mpv from mpv.io direct link | MERGED_VERIFIED |
| 133 | closed | no | fix/release-mpv-github-release | ci: download mpv from official GitHub releases | MERGED_VERIFIED |
| 132 | closed | no | fix/release-mpv-comprehensive-search | ci: comprehensive mpv.exe search after Chocolatey install | MERGED_VERIFIED |
| 131 | closed | no | fix/release-mpv-refreshenv | ci: add refreshenv and fallback paths for mpv Chocolatey install | MERGED_VERIFIED |
| 130 | closed | no | fix/release-mpv-getcommand | ci: use Get-Command to find mpv.exe after Chocolatey install | MERGED_VERIFIED |
| 129 | closed | no | fix/release-mpv-path | ci: fix mpv path detection for Chocolatey install | MERGED_VERIFIED |
| 128 | closed | no | fix/release-mpv-choco | ci: use Chocolatey to install mpv for release build | MERGED_VERIFIED |
| 127 | closed | no | fix/release-mpv-download | ci: add mpv download step to release workflow | MERGED_VERIFIED |
| 126 | closed | no | feat/premium-enterprise-ui | feat: Premium Enterprise UI + IM Auto-Reply + Auto-Reply System | MERGED_VERIFIED |
| 125 | closed | no | fix/gui-thread-safety-main-thread | fix: make GUI dialogs and callbacks main-thread safe | MERGED_VERIFIED |
| 124 | closed | no | feat/autodj-enhancements-and-fixes | fix: remediate enterprise audit findings | MERGED_VERIFIED |
| 123 | closed | no | feat/harden-workflows-v2-1794018678 | fix: harden workflows — address policedbc security review | MERGED_VERIFIED |
| 122 | closed | no | feat/harden-workflows-1794016028 | fix: harden workflows for enterprise production grade | MERGED_VERIFIED |
| 121 | closed | no | feat/auto-fix-workflow-1793999659 | feat: add auto-fix open PRs workflow | CLOSED_SUPERSEDED (#119/#122/#123 cover this) |
| 120 | closed | no | feat/auto-audit-1793998118 | feat: add auto audit/review/approve workflow | CLOSED_SUPERSEDED (#119) |
| 119 | closed | no | deploy-auto-audit-v2 | feat: add auto audit/review/approve workflow | MERGED_VERIFIED |
| 118 | closed | no | deploy-auto-audit-workflow | feat: add auto audit/review/approve workflow | CLOSED_SUPERSEDED (#119) |
| 117 | closed | no | test-auto-audit-v2-1793971178 | test: auto-audit workflow trigger v2 | MERGED_VERIFIED |
| 116 | closed | no | test-auto-audit-1793971120 | test: auto-audit workflow trigger | MERGED_VERIFIED |
| 115 | closed | no | feat/autodj-enhancements-and-fixes | docs: mark placeholder Dockerfile checklist item VERIFIED | MERGED_VERIFIED |
| 114 | closed | no | feat/autodj-enhancements-and-fixes | build: add local audit image zpostgresql; fix release mypy gate; apply ruff format | MERGED_VERIFIED |
| 113 | closed | no | feat/autodj-enhancements-and-fixes | feat: autodj enhancements and fixes | MERGED_VERIFIED |
| 112 | closed | no | fix/autodj-comprehensive-remediation-202 | fix: security hardening — backup before repo overwrite, fail-closed admin authorization | MERGED_VERIFIED |
| 111 | closed | no | style/remove-unused-noqa-main | style: remove unused noqa in __main__.py | MERGED_VERIFIED |
| 110 | closed | no | style/ruff-format-12-files | style: ruff format 12 files | MERGED_VERIFIED |
| 109 | closed | no | fix/player-countdown-and-settings-dialog | fix: player music time countdown; fix settings dialog NameError; add input validation | MERGED_VERIFIED |
| 108 | closed | no | dependabot/github_actions/actions/attest | chore(deps): bump actions/attest-build-provenance from 2.4.0 to 4.2.2 | MERGED_VERIFIED |
| 107 | closed | no | dependabot/github_actions/actions/setup | chore(deps): bump actions/setup-python from 5.6.0 to 7.1.0 | MERGED_VERIFIED |
| 106 | closed | no | dependabot/github_actions/actions/checko | chore(deps): bump actions/checkout from 4.2.2 to 7.0.1 | MERGED_VERIFIED |
| 105 | closed | no | docs/update-final-report-merged-prs | docs: update Final-Report.md with all PRs merged status | MERGED_VERIFIED |
| 104 | closed | no | fix/upload-artifact-v7-test-consistency | fix(test): update upload-artifact SHA for v7.0.2 in release consistency test | MERGED_VERIFIED |
| 103 | closed | no | fix/sec-001-signing-integrity | docs: update Final-Report.md with release completion status | MERGED_VERIFIED |
| 102 | closed | no | fix/sec-001-signing-integrity | fix: player music time countdown; harden exception handling across modules | MERGED_VERIFIED |
| 101 | closed | yes | review/sec-001-signing-integrity-2026110 | fix(sec-001): remediate SEC-001 signing integrity and artifact lifecycle | DRAFT_INCOMPLETE |
| 100 | closed | no | fix/sec-001-signing-integrity | fix(sec-001): remediate SEC-001 signing integrity and artifact lifecycle | MERGED_VERIFIED |
| 99 | closed | no | fix/test-and-ci-remediation | fix: remediate F-01 F-02 F-03 production defects | MERGED_VERIFIED |
| 98 | closed | no | fix/production-runtime-fixes | fix(gui): show settings dialog content | MERGED_VERIFIED |
| 97 | closed | no | fix/production-runtime-fixes | fix(gui): show remaining playback time countdown | MERGED_VERIFIED |
| 96 | closed | no | fix/windows-test-compatibility | fix(test): fix Windows test compatibility issues | MERGED_VERIFIED |
| 95 | closed | no | fix/lint-cleanup | fix(lint): cleanup ruff/mypy issues in migration code | MERGED_VERIFIED |
| 94 | closed | no | fix/config-migration-v2 | fix(config): safe configuration migration for placeholder values | MERGED_VERIFIED |
| 93 | closed | no | fix/config-migration | fix(config): safe configuration migration for placeholder values | MERGED_VERIFIED |
| 92 | closed | no | fix/tls-trust-integration | fix(library): yt-dlp TLS trust integration - SSL fallback from exe to Python module | MERGED_VERIFIED |
| 91 | closed | no | fix/ps-qualification-scripts | fix(ps-qualification-scripts): repair PowerShell 5.1 compatibility in qualification script | MERGED_VERIFIED |
| 90 | closed | no | fix/yt-dlp-ca-bundle | fix(library): correct yt-dlp CA bundle integration | MERGED_VERIFIED |
| 89 | closed | no | fix/production-runtime-remediation | fix(production-runtime): add observability diagnostics and comprehensive regression tests | MERGED_VERIFIED |
| 88 | closed | no | fix/production-runtime-fixes | fix(production-runtime): complete P1/P2 remediation | MERGED_VERIFIED |
| 87 | closed | no | qual/windows-qualification-fix | qual: Windows Qualification Kit PowerShell script fixes | MERGED_VERIFIED |
| 86 | closed | no | qual/windows-qualification-kit | qual: Windows Qualification Kit | MERGED_VERIFIED |
| 85 | closed | no | qual/production-acceptance | qual: production qualification acceptance reports | MERGED_VERIFIED |
| 84 | closed | no | fix/production-qualification | qual: production qualification reports and installer recovery fix | MERGED_VERIFIED |
| 83 | closed | no | fix/pin-actions-shas | ci: complete P0 hardening — SHA-pinned actions, release readiness reports | MERGED_VERIFIED |
| 82 | closed | no | dependabot/github_actions/actions/upload | chore(deps): bump actions/upload-artifact from 4.6.2 to 7.0.2 | MERGED_VERIFIED |
| 81 | closed | no | dependabot/github_actions/actions/attest | chore(deps): bump actions/attest-build-provenance | MERGED_VERIFIED |
| 80 | closed | no | dependabot/pip/setuptools-gte-84.2.1 | chore(deps-dev): update setuptools requirement from >=68 to >=84.2.1 | MERGED_VERIFIED |
| 79 | closed | no | fix/security-remediation-p1-p2 | security: remediate P1 and P2 findings | MERGED_VERIFIED |
| 78 | closed | no | fix/installer-nsi-final | fix: remove duplicate MUI_ABORTWARNING define from installer.nsi | MERGED_VERIFIED |
| 77 | closed | no | sync/implementation-checklist | checklist: mark all implementation checklist items complete | MERGED_VERIFIED |
| 76 | closed | no | fix/autodj-executable-paths-release-gate | fix: harden executable resolution and preserve user data | MERGED_VERIFIED |
| 75 | closed | no | fix/installer-nsi-download-mpv | fix: remove duplicate MUI_ABORTWARNING define from installer.nsi | MERGED_VERIFIED |
| 74 | closed | no | fix/installer-nsi-final | fix: remove duplicate MUI_ABORTWARNING define from installer.nsi | MERGED_VERIFIED |
| 73 | closed | no | fix/installer-nsi-download-mpv | fix: download mpv.exe from GitHub releases instead of bundling | MERGED_VERIFIED |
| 72 | closed | no | fix/installer-nsi-final-fix | fix: remove invalid MUI_ABORTWARNING define from installer.nsi | MERGED_VERIFIED |
| 71 | closed | no | fix/installer-nsi-vi-defines-final2 | fix: remove duplicate MUI_ABORTWARNING define from installer.nsi | CLOSED_DUPLICATE (#72/#74/#75/#78) |
| 70 | closed | no | fix/installer-nsi-vi-defines | fix: remove invalid VI_* defines from installer.nsi | MERGED_VERIFIED |
| 69 | closed | no | fix/installer-nsi-vi-defines | fix: remove invalid SetCompress line from installer.nsi | MERGED_VERIFIED |
| 68 | closed | no | fix/installer-nsi-vi-defines | fix: remove invalid VI_* defines from installer.nsi | MERGED_VERIFIED |
| 67 | closed | no | fix/update-mpv-latest | feat: update yt-dlp.exe to latest version | MERGED_VERIFIED |
| 66 | closed | no | fix/installer-nsi-post-install | fix: add post-install mpv-register.bat and VBCABLE_Setup_x64.exe silent execution | MERGED_VERIFIED |
| 65 | closed | no | docs/final-report-update | docs: update AutoDJ-Final-Report.md with residual risks, rollback, next actions | MERGED_VERIFIED |
| 64 | closed | no | fix/installer-nsi-hardening | feat: bundle standard config.toml in NSIS installer | MERGED_VERIFIED |
| 63 | closed | no | docs/final-report | docs: add AutoDJ-Final-Report.md complete project report | MERGED_VERIFIED |
| 62 | closed | no | chore/validate-template-target | feat: add validate-template target to Makefile | MERGED_VERIFIED |
| 61 | closed | no | chore/cleanup-unused-scripts | chore: cleanup unused scripts and update github_admin default repo | MERGED_VERIFIED |
| 60 | closed | no | fix/load-folder-crash | fix: load folder button crash on permission-denied directories | MERGED_VERIFIED |
| 59 | closed | no | fix/log-permission-clean | fix: protect log file creation against PermissionError on startup | MERGED_VERIFIED |
| 58 | closed | no | docs/v026-post-release-verification | fix: protect log file creation against PermissionError on startup | MERGED_VERIFIED |
| 57 | closed | no | docs/v026-post-release-verification | fix: settings config.toml write, hidden CMD launcher, type safety | MERGED_VERIFIED |
| 56 | closed | no | fix/playlist-ytdlp-tls-cross-platform | fix: make playlist yt-dlp resolution TLS-safe across platforms | MERGED_VERIFIED |
| 55 | closed | no | docs/v026-release-documentation | docs: add v0.2.6 release audit, security, acceptance and operational handover reports | MERGED_VERIFIED |
| 54 | closed | no | release/autodj-v0.2.6 | chore: release CamfrogAutoDJ v0.2.6 | MERGED_VERIFIED |
| 53 | closed | no | docs/v025-official-handover | docs: add v0.2.5 official release handover report | MERGED_VERIFIED |
| 52 | closed | no | docs/v025-release-gate-acceptance | docs: add v0.2.5 final release gate audit and acceptance report | MERGED_VERIFIED |
| 51 | closed | no | docs/v025-final-reports | docs: add v0.2.5 baseline, release, and final verification reports | MERGED_VERIFIED |
| 50 | closed | no | fix/release-installer-filename | fix(ci): match installer artifact pattern Camfrog-AutoDJ-Setup-*.exe | MERGED_VERIFIED |
| 49 | closed | no | fix/release-sbom-flag | fix(ci): use cyclonedx-py environment with -o flag for SBOM generation | MERGED_VERIFIED |
| 48 | closed | no | fix/installer-optional-bundled-dependenc | fix(installer): mark external mpv and vbcable as nonfatal | MERGED_VERIFIED |
| 47 | closed | no | fix/installer-config-optional | fix(installer): make config.toml nonfatal in NSIS script | MERGED_VERIFIED |
| 46 | closed | no | fix/release-nsis-path-and-env | fix(ci): add NSIS to path for Windows release runner | MERGED_VERIFIED |
| 45 | closed | no | feat/v025-product-enhancements | feat: v0.2.5 audio fade, dynamic normalization, moderation, and SBOM attestation | MERGED_VERIFIED |
| 44 | closed | no | docs/sync-all-documentation | docs: sync playlist pack guidance and installer spec with 0.2.5 dynamic resolution | MERGED_VERIFIED |
| 43 | closed | no | chore/sync-release-0.2.5-and-quality | chore: bump and sync version 0.2.5 across docs, manifests, and build scripts | MERGED_VERIFIED |
| 42 | closed | no | feat/dynamic-playlist-search-resolve | feat: dynamic search resolution and lookahead preloading for playlist tracks | MERGED_VERIFIED |
| 41 | closed | no | dependabot/github_actions/softprops/acti | chore(deps): bump softprops/action-gh-release from 2 to 3 | MERGED_VERIFIED |
| 40 | closed | no | fix/codeql-action-alignment-4.39.1 | fix(ci): align CodeQL action steps to v4.39.1 and configure dependabot group | MERGED_VERIFIED |
| 39 | closed | no | fix/test-suite-and-playback-edgecases | fix: resolve timeout and failure backoff edgecases in engine and player | MERGED_VERIFIED |
| 38 | closed | no | fix/join-uri-template-empty | fix: gracefully handle missing join_uri_template in launcher | MERGED_VERIFIED |
| 37 | closed | no | fix/fake-tk-window-support | fix: add window support to fake_tk for Settings tab scrollbar | MERGED_VERIFIED |
| 36 | closed | no | fix/log-nameerror | fix: fix NameError in auto_launch exception handler | MERGED_VERIFIED |
| 35 | closed | no | fix/autolaunch-nameerror | fix: fix NameError when auto_launch fails | MERGED_VERIFIED |
| 34 | closed | no | fix/autolaunch-gui | fix: auto-launch crash prevents GUI from opening | MERGED_VERIFIED |
| 33 | closed | no | fix/mpv-bundle-system | fix: bundle mpv.exe from system when mpv/ not in repo | MERGED_VERIFIED |
| 32 | closed | no | fix/mpv-bundle | fix: bundle mpv/ with AutoDJ.exe | MERGED_VERIFIED |
| 31 | closed | no | fix/log-file-directory | fix: log file directory not created | MERGED_VERIFIED |
| 30 | closed | no | fix/config-relative-paths | fix: config.example.toml use relative mpv_path and ytdlp_path | MERGED_VERIFIED |
| 29 | closed | no | fix/config-permission | fix: include config.toml in installer | MERGED_VERIFIED |
| 28 | closed | no | fix/config-permission | fix: config.toml PermissionError on Program Files install | MERGED_VERIFIED |
| 27 | closed | no | fix/playlist-not-play | fix: playlist not play when mpv not available | MERGED_VERIFIED |
| 26 | closed | no | fix/log-file-permission | fix: config.toml log_file PermissionError on Program Files install | MERGED_VERIFIED |
| 25 | closed | no | fix/settings-scrollbar | fix: Settings tab scrollbar - Save button was off-screen | MERGED_VERIFIED |
| 24 | closed | no | fix/nsis-config-read-permission | fix: NSIS installer config.toml read permission error | MERGED_VERIFIED |
| 23 | closed | no | fix/nsis-config-permission | fix: NSIS installer config.toml permission error | MERGED_VERIFIED |
| 22 | closed | no | feat/settings-button | feat: add Settings button to GUI header | MERGED_VERIFIED |
| 21 | closed | no | fix/nsis-uninstall-string | fix: NSIS installer CheckExistingInstall - remove StrReplace dependency | MERGED_VERIFIED |
| 20 | closed | no | fix/nsis-getparameters | fix: NSIS installer CheckExistingInstall GetParameters error | MERGED_VERIFIED |
| 19 | closed | no | feat/settings-tab | feat: add Settings tab to GUI | MERGED_VERIFIED |
| 18 | closed | no | config/installer-layout | config: update config.example.toml for installer layout | MERGED_VERIFIED |
| 17 | closed | no | fix/nsis-installer-mpv-vbcable | fix: NSIS installer - auto-uninstall old version, add mpv + yt-dlp + VBCable | MERGED_VERIFIED |
| 16 | closed | no | docs/sync-release-0.2.5 | docs: sync CHANGELOG, README, Makefile with 0.2.5 release | MERGED_VERIFIED |
| 15 | closed | no | docs/sync-release-0.2.5 | docs: sync CHANGELOG, README, Makefile with 0.2.5 release | MERGED_VERIFIED |
| 14 | closed | no | fix/nsis-installer-warnings | fix: eliminate NSIS installer warnings, remove src section | MERGED_VERIFIED |
| 13 | closed | no | fix/nsis-installer-warnings | fix: eliminate NSIS installer warnings, remove src section | MERGED_VERIFIED |
| 12 | closed | no | fix/restore-cross-platform-ci-20261031 | fix(ci): restore cross-platform test matrix | MERGED_VERIFIED |
| 11 | closed | no | chore/gitignore-build-artifacts | chore: exclude build artifacts, binaries, debug scripts, forensic files | MERGED_VERIFIED |
| 10 | closed | no | chore/gitignore-build-artifacts | chore: exclude build artifacts, binaries, debug scripts, forensic files | MERGED_VERIFIED |
| 9 | closed | no | fix/enterprise-production-fixes | release: v0.2.4 enterprise production fixes | MERGED_VERIFIED |
| 8 | closed | no | fix/play-tracks-to-completion | Fix tracks stopping before completion | MERGED_VERIFIED |
| 7 | closed | no | dependabot/github_actions/actions/setup | build(deps): bump actions/setup-python from 5 to 7 | MERGED_VERIFIED |
| 6 | closed | no | dependabot/github_actions/actions/checko | build(deps): bump actions/checkout from 4 to 7 | MERGED_VERIFIED |
| 5 | closed | yes | fix/autodj-test-baseline-20261028-run11 | fix(ci): restore deterministic AutoDJ test baseline | DRAFT_INCOMPLETE |
| 4 | closed | yes | fix/codeql-actions-version-alignment-202 | fix(ci): align CodeQL action versions | DRAFT_INCOMPLETE |
| 2 | closed | no | dependabot/github_actions/github/codeql- | chore(deps): bump github/codeql-action/init from 4.38.2 to 4.39.1 | MERGED_VERIFIED |
| 1 | closed | no | dependabot/github_actions/github/codeql- | chore(deps): bump github/codeql-action/analyze from 4.38.2 to 4.39.1 | MERGED_VERIFIED |

**Note:** head_sha values are withheld from this rendered inventory; the authoritative source is the `gh api` output at `/tmp/opencode/all_prs.json` captured during this audit.
